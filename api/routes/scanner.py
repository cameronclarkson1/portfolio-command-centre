"""
scanner.py — Daily market scanner: S&P 500 + Dow Jones + NASDAQ-100.

Universe is a hardcoded curated list of ~120 large-cap US stocks covering
all Dow 30 components, NASDAQ-100 top holdings, and S&P 500 top holdings.
This avoids needing any FMP constituent/screener endpoint.

Deep analysis (quote + key_metrics + income) on all tickers.
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
# Updated periodically — compositions are stable across quarters.

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
    """Return the hardcoded large-cap universe."""
    return UNIVERSE


# ── Deep analysis per stock ───────────────────────────────────────────────────

def _analyse_one(ticker: str, info: dict) -> dict | None:
    """
    Run 3 parallel API calls per stock: quote + key_metrics + income_statement.
    Builds a composite score (0–100) and returns an enriched result dict.
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

        price      = quote.get("price")      or 0
        yr_h       = quote.get("year_high")  or 0
        yr_l       = quote.get("year_low")   or 0
        change_pct = quote.get("change_pct")
        name       = quote.get("name")       or profile.get("name")  or ticker
        sector     = profile.get("sector")   or info.get("sector")   or ""
        market_cap = quote.get("market_cap") or profile.get("market_cap")

        # get_quote doesn't map pe — fetch it from quote raw via key_metrics
        # pe comes from income data instead
        roic      = key_m.get("roic")
        ev_ebitda = key_m.get("ev_ebitda")

        # Net margin from latest quarter
        net_margin = income[0].get("net_margin") if income else None

        # Revenue growth: trailing 4Q vs prior 4Q
        rev_growth = None
        if len(income) >= 8:
            latest_4 = sum((q.get("revenue") or 0) for q in income[:4])
            prior_4  = sum((q.get("revenue") or 0) for q in income[4:8])
            if prior_4 > 0:
                rev_growth = (latest_4 - prior_4) / prior_4

        # Free cash flow — from income operating_income as proxy if needed
        # We'll use ROIC as quality signal since we dropped cash flow call
        fcf_positive = None  # not fetched in this simplified version

        # ── Composite score (0–100) ────────────────────────────────────────────
        score = 50.0

        # Quality (ROIC is the strongest signal)
        if roic and roic > 0.25:   score += 20
        elif roic and roic > 0.15: score += 12
        elif roic and roic > 0.08: score += 5
        elif roic and roic < 0:    score -= 18

        # Valuation (EV/EBITDA)
        if ev_ebitda and 0 < ev_ebitda <= 8:    score += 18
        elif ev_ebitda and 8 < ev_ebitda <= 15: score += 8
        elif ev_ebitda and ev_ebitda > 25:      score -= 12

        # Profitability (net margin)
        if net_margin and net_margin > 0.25:   score += 12
        elif net_margin and net_margin > 0.12: score += 6
        elif net_margin and net_margin > 0:    score += 2
        elif net_margin and net_margin < 0:    score -= 12

        # Growth (revenue YoY)
        if rev_growth and rev_growth > 0.20:    score += 12
        elif rev_growth and rev_growth > 0.08:  score += 6
        elif rev_growth and rev_growth < -0.05: score -= 8

        # Price vs 52-week range (near low = potential value)
        if yr_h > yr_l > 0 and price > 0:
            pct_from_low = (price - yr_l) / (yr_h - yr_l)
            if pct_from_low < 0.25:   score += 10
            elif pct_from_low < 0.45: score += 4

        score = round(max(0.0, min(100.0, score)), 1)

        return {
            "ticker":      ticker,
            "name":        name,
            "sector":      sector,
            "price":       price,
            "change_pct":  change_pct,
            "market_cap":  market_cap,
            "pe_ratio":    None,
            "ev_ebitda":   round(ev_ebitda, 1) if ev_ebitda else None,
            "roic":        round(roic * 100, 1) if roic else None,
            "net_margin":  round(net_margin * 100, 1) if net_margin else None,
            "rev_growth":  round(rev_growth * 100, 1) if rev_growth else None,
            "fcf_positive": None,
            "year_high":   yr_h or None,
            "year_low":    yr_l or None,
            "score":       score,
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

        # Step 1 — hardcoded universe
        tickers = _get_universe()
        print(f"[scanner] Universe: {len(tickers)} stocks")
        _state["stocks_scanned"] = len(tickers)

        # Step 2 — deep analysis on all tickers (3 concurrent calls per stock, 5 at a time)
        print("[scanner] Running deep analysis…")
        results: list[dict] = []
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(_analyse_one, ticker, {}): ticker for ticker in tickers}
            for fut in as_completed(futures):
                r = fut.result()
                if r:
                    results.append(r)

        # Step 3 — sort by score, keep top 20
        results.sort(key=lambda x: x["score"], reverse=True)
        top_20 = results[:20]

        # Step 4 — persist
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
