"""
scanner.py — Daily market scanner: S&P 500 + Dow Jones + NASDAQ-100.

Universe is a hardcoded curated list of ~120 large-cap US stocks covering
all Dow 30 components, NASDAQ-100 top holdings, and S&P 500 top holdings.
This avoids needing any FMP constituent/screener endpoint.

Scoring: quality (ROIC, margins) + sector-relative valuation (EV/EBITDA, P/E)
+ growth (revenue YoY) + safety (current ratio) + price position (52-week).
High score = high quality AND reasonably valued vs sector peers.

Runs automatically at 4:15 PM ET Mon-Fri via APScheduler.
Persists top 20 results to disk.
"""

import json
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from fastapi import APIRouter
import providers.fmp_provider as fmp

router = APIRouter()

# ── Storage ───────────────────────────────────────────────────────────────────

RESULTS_FILE = Path(__file__).parent.parent / "data" / "scanner_results.json"
RESULTS_FILE.parent.mkdir(exist_ok=True)

_state = {
    "running":             False,
    "last_run":            None,
    "last_run_duration_s": None,
    "stocks_scanned":      0,
    "error":               None,
}

# ── Hardcoded universe ────────────────────────────────────────────────────────
# Covers all Dow 30 + NASDAQ-100 top 50 + S&P 500 top 50 (deduplicated).

_DOW_30 = [
    "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW",
    "GS",   "HD",   "HON", "IBM", "INTC", "JNJ", "JPM", "KO",  "MCD", "MMM",
    "MRK",  "MSFT", "NKE", "PG",  "TRV", "UNH", "V",   "VZ",  "WBA", "WMT",
]

_NASDAQ_100_TOP = [
    "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "NFLX", "AMD",
    "ADBE", "QCOM", "INTU", "TXN",   "BKNG", "ISRG", "REGN", "VRTX", "MU",
    "PANW", "LRCX", "KLAC", "SNPS",  "CDNS", "ADI",  "AMAT", "GILD", "MELI",
    "MNST", "PYPL", "ROST", "PAYX",  "DXCM", "BIIB", "MRNA", "CRWD", "ABNB",
    "FAST", "MCHP", "ODFL", "ADSK",  "EBAY", "CPRT", "WDAY", "TEAM", "DDOG",
    "ORLY", "PCAR", "KDP",  "EXC",   "FTNT",
]

_SP500_TOP = [
    "LLY",  "XOM",  "MA",   "UNH",  "ABBV", "ACN",  "TMO",  "ORCL", "ABT",
    "PM",   "LIN",  "DHR",  "GE",   "MS",   "BMY",  "PFE",  "T",    "RTX",
    "BLK",  "SYK",  "ZTS",  "MDT",  "PEP",  "SPGI", "NOW",  "C",    "UBER",
    "NEE",  "SO",   "DUK",  "CB",   "ITW",  "CME",  "EOG",  "SLB",  "SHW",
    "CL",   "BDX",  "ELV",  "TJX",  "AMT",  "CI",   "CVS",  "MO",   "DE",
    "MMC",  "SCHW", "COP",  "PLD",  "F",    "GM",   "BAC",  "WFC",  "USB",
    "PNC",  "MCO",  "SBUX", "NOC",  "LMT",  "GD",   "HUM",  "ANTM", "IDXX",
]

UNIVERSE: list[str] = sorted(set(_DOW_30 + _NASDAQ_100_TOP + _SP500_TOP))


def _get_universe() -> list[str]:
    return UNIVERSE


# ── Sector benchmarks for relative valuation ─────────────────────────────────
# These are long-run median multiples per sector.
# A stock trading at 2x its sector benchmark gets penalised; at 0.6x gets rewarded.

_SECTOR_EV_EBITDA: dict[str, float] = {
    "Technology":              22.0,
    "Communication Services":  16.0,
    "Healthcare":              18.0,
    "Consumer Discretionary":  15.0,
    "Consumer Staples":        13.0,
    "Industrials":             14.0,
    "Financials":              12.0,
    "Energy":                   9.0,
    "Utilities":               10.0,
    "Real Estate":             18.0,
    "Materials":               10.0,
}
_DEFAULT_EV_EBITDA = 15.0

_SECTOR_PE: dict[str, float] = {
    "Technology":              28.0,
    "Communication Services":  22.0,
    "Healthcare":              24.0,
    "Consumer Discretionary":  22.0,
    "Consumer Staples":        20.0,
    "Industrials":             20.0,
    "Financials":              14.0,
    "Energy":                  14.0,
    "Utilities":               17.0,
    "Real Estate":             35.0,
    "Materials":               16.0,
}
_DEFAULT_PE = 20.0

# Financials and Real Estate don't use current_ratio (banks fund differently)
_SKIP_CURRENT_RATIO = {"Financials", "Real Estate"}


# ── Continuous scoring helper ─────────────────────────────────────────────────

def _interp(value: float, breakpoints: list[tuple[float, float]]) -> float:
    """
    Linear interpolation between (x, y) breakpoints.
    Returns y0 if value < first x, yN if value > last x.
    """
    if value <= breakpoints[0][0]:
        return breakpoints[0][1]
    if value >= breakpoints[-1][0]:
        return breakpoints[-1][1]
    for i in range(len(breakpoints) - 1):
        x1, y1 = breakpoints[i]
        x2, y2 = breakpoints[i + 1]
        if x1 <= value <= x2:
            t = (value - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return breakpoints[-1][1]


# ── Deep analysis per stock ───────────────────────────────────────────────────

def _analyse_one(ticker: str, info: dict, pe_prefetch: float | None = None) -> dict | None:
    """
    Run 3 parallel API calls per stock: quote + key_metrics + income_statement.
    Builds a composite score (0–100) using quality + sector-relative valuation
    + growth + safety signals.
    """
    try:
        with ThreadPoolExecutor(max_workers=4) as ex:
            q_f   = ex.submit(fmp.get_quote, ticker)
            km_f  = ex.submit(fmp.get_key_metrics, ticker, 1)
            inc_f = ex.submit(fmp.get_income_statement, ticker, 8)
            pr_f  = ex.submit(fmp.get_company_profile, ticker)

            try:
                quote = q_f.result(timeout=20)
            except Exception:
                quote = {}
            try:
                key_m = (km_f.result(timeout=20) or [{}])[0]
            except Exception:
                key_m = {}
            try:
                income = inc_f.result(timeout=20) or []
            except Exception:
                income = []
            try:
                profile = pr_f.result(timeout=20)
            except Exception:
                profile = {}

        price         = quote.get("price")      or 0
        yr_h          = quote.get("year_high")  or 0
        yr_l          = quote.get("year_low")   or 0
        change_pct    = quote.get("change_pct")
        name          = quote.get("name")       or profile.get("name")  or ticker
        sector        = profile.get("sector")   or info.get("sector")   or ""
        market_cap    = quote.get("market_cap") or profile.get("market_cap")

        roic          = key_m.get("roic")
        ev_ebitda     = key_m.get("ev_ebitda")
        current_ratio = key_m.get("current_ratio")

        # Net margin from latest quarter
        net_margin = income[0].get("net_margin") if income else None

        # Revenue growth: trailing 4 quarters vs prior 4 quarters
        rev_growth = None
        if len(income) >= 8:
            latest_4 = sum((q.get("revenue") or 0) for q in income[:4])
            prior_4  = sum((q.get("revenue") or 0) for q in income[4:8])
            if prior_4 > 0:
                rev_growth = (latest_4 - prior_4) / prior_4

        # PE ratio: from batch pre-fetch (more reliable) or None
        pe_ratio = pe_prefetch

        # ── Composite score (0–100) ────────────────────────────────────────────
        # Starts at 50. Each factor adds or subtracts based on quality/value signal.
        # Range of each factor is noted in comments.

        score = 50.0

        # ── Quality: ROIC (-18 to +20) ────────────────────────────────────────
        if roic is not None:
            if roic < 0:
                score -= 18
            else:
                score += _interp(roic, [(0, 0), (0.10, 8), (0.20, 15), (0.30, 20)])

        # ── Quality: Net margin (-12 to +12) ──────────────────────────────────
        # Uses sector-neutral thresholds — high-margin tech and low-margin retail
        # both score fairly since this is about absolute profitability quality.
        if net_margin is not None:
            if net_margin < 0:
                score -= 12
            else:
                score += _interp(net_margin, [(0, 0), (0.05, 3), (0.12, 7), (0.25, 12)])

        # ── Valuation: EV/EBITDA vs sector benchmark (-12 to +18) ────────────
        # A company at 0.6x its sector's typical multiple scores +18.
        # At 2x+ the benchmark it gets penalised — overvalued vs peers.
        if ev_ebitda and ev_ebitda > 0:
            benchmark = _SECTOR_EV_EBITDA.get(sector, _DEFAULT_EV_EBITDA)
            ratio     = ev_ebitda / benchmark
            score += _interp(ratio, [
                (0.0,  18),  # deeply cheap vs sector
                (0.6,  16),
                (1.0,   8),  # at sector fair value
                (1.5,   2),
                (2.0,  -5),  # 2x sector median — meaningfully expensive
                (3.0, -12),  # 3x sector median — very expensive
            ])

        # ── Valuation: P/E vs sector benchmark (-8 to +12) ───────────────────
        # Negative PE (loss-making) not penalised here — ROIC and margin handle it.
        # Skip if no PE data available (neutral — don't penalise missing data).
        if pe_ratio and pe_ratio > 0:
            pe_bench = _SECTOR_PE.get(sector, _DEFAULT_PE)
            pe_pct   = pe_ratio / pe_bench
            score += _interp(pe_pct, [
                (0.0,  12),
                (0.6,  11),
                (1.0,   6),  # at sector fair value
                (1.5,   1),
                (2.0,  -4),
                (3.0,  -8),
            ])

        # ── Growth: Revenue YoY (-8 to +12) ───────────────────────────────────
        if rev_growth is not None:
            if rev_growth < -0.05:
                score -= 8
            else:
                score += _interp(rev_growth, [
                    (0.00,  0),
                    (0.05,  4),
                    (0.10,  7),
                    (0.20, 12),
                ])

        # ── Safety: Current ratio (-5 to +8) ──────────────────────────────────
        # Skipped for Financials and Real Estate (banks fund differently).
        if current_ratio is not None and sector not in _SKIP_CURRENT_RATIO:
            if current_ratio < 1.0:
                score -= 5
            else:
                score += _interp(current_ratio, [(1.0, 0), (1.5, 4), (2.0, 8)])

        # ── Price position: 52-week range (0 to +8) ───────────────────────────
        # Near the 52-week low = potential value not yet priced in.
        if yr_h > yr_l > 0 and price > 0:
            pct_from_low = (price - yr_l) / (yr_h - yr_l)
            score += _interp(pct_from_low, [(0.0, 8), (0.25, 4), (0.45, 0)])

        score = round(max(0.0, min(100.0, score)), 1)

        return {
            "ticker":        ticker,
            "name":          name,
            "sector":        sector,
            "price":         price,
            "change_pct":    change_pct,
            "market_cap":    market_cap,
            "pe_ratio":      round(pe_ratio, 1) if pe_ratio else None,
            "ev_ebitda":     round(ev_ebitda, 1) if ev_ebitda else None,
            "roic":          round(roic * 100, 1) if roic else None,
            "net_margin":    round(net_margin * 100, 1) if net_margin else None,
            "rev_growth":    round(rev_growth * 100, 1) if rev_growth else None,
            "current_ratio": round(current_ratio, 2) if current_ratio else None,
            "year_high":     yr_h or None,
            "year_low":      yr_l or None,
            "score":         score,
        }

    except Exception as e:
        print(f"[scanner] Analysis failed for {ticker}: {e}")
        return None


# ── Main scan orchestrator ────────────────────────────────────────────────────

def run_daily_scan() -> dict:
    """
    Full daily scan. Called at 4:15 PM ET automatically or via /trigger.
    """
    if _state["running"]:
        return {"error": "Scan already in progress"}

    _state["running"] = True
    _state["error"]   = None
    started_at = datetime.now(timezone.utc)

    try:
        print("[scanner] ── Starting daily scan ─────────────────────────────")

        tickers = _get_universe()
        print(f"[scanner] Universe: {len(tickers)} stocks")
        _state["stocks_scanned"] = len(tickers)

        # Pre-fetch PE ratios for the full universe using batch quotes (50 per call).
        # Batch endpoint returns PE from the FMP quote feed; single /quote does not.
        print("[scanner] Pre-fetching PE ratios via batch quotes…")
        pe_map: dict[str, float | None] = {}
        for i in range(0, len(tickers), 50):
            batch = tickers[i : i + 50]
            try:
                for q in fmp.get_batch_quotes(batch):
                    if q.get("pe_ratio") and q["pe_ratio"] > 0:
                        pe_map[q["ticker"]] = q["pe_ratio"]
            except Exception as e:
                print(f"[scanner] Batch quote error (offset {i}): {e}")

        print(f"[scanner] PE ratios fetched for {len(pe_map)}/{len(tickers)} tickers")

        # Deep analysis on all tickers (3 concurrent calls per stock, 5 stocks at a time)
        print("[scanner] Running deep analysis…")
        results: list[dict] = []
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {
                ex.submit(_analyse_one, ticker, {}, pe_map.get(ticker)): ticker
                for ticker in tickers
            }
            for fut in as_completed(futures):
                r = fut.result()
                if r:
                    results.append(r)

        results.sort(key=lambda x: x["score"], reverse=True)
        top_20 = results[:20]

        duration = round((datetime.now(timezone.utc) - started_at).total_seconds(), 1)
        payload = {
            "scanned_at":       started_at.isoformat(),
            "duration_seconds": duration,
            "universe_size":    len(tickers),
            "stocks_quoted":    len(results),
            "opportunities":    top_20,
        }
        RESULTS_FILE.write_text(json.dumps(payload, indent=2))

        _state.update({
            "running":             False,
            "last_run":            started_at.isoformat(),
            "last_run_duration_s": duration,
            "error":               None,
        })
        print(f"[scanner] Done — {len(top_20)} opportunities in {duration}s")
        return payload

    except Exception as e:
        _state.update({"running": False, "error": str(e)})
        print(f"[scanner] Scan failed: {e}")
        raise


# ── API Endpoints ─────────────────────────────────────────────────────────────

@router.get("/status")
def get_status():
    return {
        "running":             _state["running"],
        "last_run":            _state["last_run"],
        "last_run_duration_s": _state["last_run_duration_s"],
        "stocks_scanned":      _state["stocks_scanned"],
        "error":               _state["error"],
        "results_available":   RESULTS_FILE.exists(),
    }


@router.get("/results")
def get_results():
    if not RESULTS_FILE.exists():
        return {
            "opportunities": [],
            "scanned_at":    None,
            "message":       "No results yet — scan runs automatically at 4:15 PM ET on market days.",
        }
    try:
        return json.loads(RESULTS_FILE.read_text())
    except Exception:
        return {"opportunities": [], "scanned_at": None, "message": "Error reading results file"}


def _do_trigger():
    if _state["running"]:
        return {"message": "Scan already in progress", "running": True}
    threading.Thread(target=run_daily_scan, daemon=True).start()
    return {"message": "Scan started", "running": True}

@router.post("/trigger")
def trigger_scan():
    return _do_trigger()

@router.get("/trigger")
def trigger_scan_get():
    """GET version — paste into browser to trigger manually."""
    return _do_trigger()
