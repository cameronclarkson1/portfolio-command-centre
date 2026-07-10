"""
portfolio.py — /api/portfolio and /api/portfolio/risk endpoints.

Ports the live-portfolio logic from repo/pages/risk_centre.py into
FastAPI so the Next.js frontend receives real computed data instead
of merging prices client-side from mock records.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, Query
from utils.sample_data import PORTFOLIO_HOLDINGS, PORTFOLIO_SUMMARY, WATCHLIST
from services import market_data_service

router = APIRouter()

# ── Risk limits (mirrored from risk_centre.py) ────────────────────────────────
_POS_CAP      = 10.0
_POS_TARGET   = (4.0, 8.0)
_SECTOR_SOFT  = 25.0
_SECTOR_HARD  = 30.0
_CASH_MIN     = 5.0
_CASH_TARGET  = 10.0
_CASH_MAX     = 15.0
_BETA_TARGET  = (0.8, 1.2)
_BETA_ALERT   = 1.3

# Fair-value lookup from watchlist (for overvaluation check)
_WL_FV: dict[str, float] = {
    s["ticker"]: s["fair_value"]
    for s in WATCHLIST
    if s.get("fair_value")
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_base_holdings() -> list[dict]:
    """
    Return the base holdings list — tries Sharesight first, falls back to sample_data.
    Sharesight provides: ticker, name, sector, shares, avg_cost, current_price.
    """
    try:
        import providers.sharesight_provider as sharesight
        from config.api_keys import SHARESIGHT_ACCESS_TOKEN
        if SHARESIGHT_ACCESS_TOKEN:
            holdings = sharesight.get_holdings()
            if holdings:
                return holdings
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Sharesight unavailable, using sample_data: {e}")
    return list(PORTFOLIO_HOLDINGS)


def _build_live_portfolio():
    """
    Fetch live prices and recompute per-holding metrics.
    Ported directly from risk_centre.py._build_live_portfolio().

    Returns: (holdings, sector_weights, total_value, total_invested,
               cash, cash_pct, daily_change_dollars, daily_change_pct, prices_live)
    """
    base_holdings = _get_base_holdings()
    tickers = [h["ticker"] for h in base_holdings]
    try:
        live_prices = market_data_service.get_portfolio_prices(tickers) or {}
    except Exception:
        live_prices = {}

    prices_live = False
    holdings: list[dict] = []

    for h in base_holdings:
        item = h.copy()
        pd   = live_prices.get(h["ticker"])

        if pd and pd.get("price"):
            item["current_price"] = pd["price"]
            item["change_pct"]    = pd.get("change_pct", 0.0) or 0.0
            prices_live = True
        else:
            item.setdefault("current_price", h.get("current_price", 0.0))
            item["change_pct"] = 0.0

        price    = item["current_price"]
        shares   = item["shares"]
        avg_cost = item["avg_cost"]

        item["market_value"]         = round(price * shares, 2)
        item["cost_basis"]           = round(avg_cost * shares, 2)
        item["unrealised_pnl"]       = round(item["market_value"] - item["cost_basis"], 2)
        item["unrealised_pct"]       = round(
            item["unrealised_pnl"] / item["cost_basis"] * 100
            if item["cost_basis"] else 0, 2
        )
        item["daily_change_dollars"] = round(item["market_value"] * item["change_pct"] / 100, 2)
        holdings.append(item)

    total_invested = sum(h["market_value"] for h in holdings)
    cash           = PORTFOLIO_SUMMARY["cash"]
    total_value    = total_invested + cash

    for item in holdings:
        item["weight"] = round(
            item["market_value"] / total_value * 100 if total_value else 0, 2
        )

    sector_weights: dict[str, float] = {}
    for item in holdings:
        s = item["sector"]
        sector_weights[s] = round(sector_weights.get(s, 0) + item["weight"], 2)

    cash_pct             = round(cash / total_value * 100, 2) if total_value else 0
    daily_change_dollars = round(sum(h["daily_change_dollars"] for h in holdings), 2)
    daily_change_pct     = round(daily_change_dollars / total_value * 100, 4) if total_value else 0

    return (
        holdings, sector_weights, total_value, total_invested,
        cash, cash_pct, daily_change_dollars, daily_change_pct, prices_live,
    )


def _build_risk_categories(holdings: list, sector_weights: dict, cash_pct: float) -> list:
    """
    Compute 6 risk category cards from live portfolio metrics.
    Ported from risk_centre.py._build_risk_categories().
    """
    if not holdings:
        return []

    # 1. Position Concentration
    max_pos    = max(holdings, key=lambda h: h.get("weight", 0))
    max_weight = max_pos.get("weight", 0)
    pos_sev    = (
        "critical" if max_weight >= _POS_CAP
        else "warning" if max_weight >= _POS_TARGET[1]
        else "info"
    )
    pos_score = max(0, min(100, int(100 - max(0, max_weight - _POS_TARGET[0]) * 8)))

    # 2. Sector Concentration
    max_sec     = max(sector_weights, key=sector_weights.get)
    max_sec_pct = sector_weights[max_sec]
    sec_sev     = (
        "critical" if max_sec_pct >= _SECTOR_HARD
        else "warning" if max_sec_pct >= _SECTOR_SOFT
        else "info"
    )
    sec_score   = max(0, min(100, int(100 - max(0, max_sec_pct - 20) * 4)))
    sec_tickers = [h["ticker"] for h in holdings if h["sector"] == max_sec]

    # 3. Cash Level
    dist       = abs(cash_pct - _CASH_TARGET)
    cash_sev   = (
        "critical" if cash_pct < _CASH_MIN or cash_pct > _CASH_MAX
        else "warning" if dist > 4
        else "info"
    )
    cash_score = max(0, min(100, int(100 - dist * 5)))
    if cash_pct > _CASH_MAX:
        cash_desc   = f"Cash at {cash_pct:.1f}% — above maximum. Too much idle capital."
        cash_action = "Deploy into rated Buy/Add positions from the watchlist."
    elif cash_pct < _CASH_MIN:
        cash_desc   = f"Cash at {cash_pct:.1f}% — below minimum. Insufficient dry powder."
        cash_action = "Raise cash by trimming overweight positions before buying anything new."
    else:
        cash_desc   = f"Cash at {cash_pct:.1f}% — within the {_CASH_MIN:.0f}–{_CASH_MAX:.0f}% target band."
        cash_action = (
            "Maintain current cash level." if dist < 2
            else "Monitor and rebalance as trades execute."
        )

    # 4. Portfolio Beta (stored value — live computation requires historical returns)
    beta       = PORTFOLIO_SUMMARY.get("portfolio_beta", 1.0)
    beta_ok    = _BETA_TARGET[0] <= beta <= _BETA_TARGET[1]
    beta_sev   = (
        "critical" if beta > _BETA_ALERT or beta < 0.5
        else "warning" if not beta_ok
        else "info"
    )
    beta_score = max(0, min(100, int(100 - abs(beta - 1.0) * 40)))
    beta_dir   = "amplify" if beta > 1 else "dampen"

    # 5. Overvaluation Risk
    overvalued = []
    for h in holdings:
        fv = _WL_FV.get(h["ticker"])
        if fv and h.get("current_price") and h["current_price"] > fv:
            overvalued.append((h["ticker"], (h["current_price"] / fv - 1) * 100))
    overvalued.sort(key=lambda x: -x[1])
    n_ov      = len(overvalued)
    ov_sev    = "critical" if n_ov >= 4 else ("warning" if n_ov >= 2 else "info")
    ov_score  = max(0, min(100, int(100 - n_ov * 12)))
    if overvalued:
        ov_tickers = ", ".join(f"{t} (+{p:.0f}%)" for t, p in overvalued[:3])
        ov_desc    = f"{n_ov} holding{'s' if n_ov > 1 else ''} above fair value: {ov_tickers}."
        ov_action  = "Do not add to overvalued positions. Consider trimming if significantly above fair value."
    else:
        ov_desc   = "All holdings are at or below estimated fair value — good upside remaining."
        ov_action = "Continue adding to positions within buy range per the watchlist plan."

    # 6. Drawdown & Liquidity (top-3 combined weight)
    sorted_h  = sorted(holdings, key=lambda h: h.get("weight", 0), reverse=True)
    top3_w    = sum(h.get("weight", 0) for h in sorted_h[:3])
    top3_tix  = ", ".join(h["ticker"] for h in sorted_h[:3])
    liq_sev   = "critical" if top3_w > 40 else ("warning" if top3_w > 30 else "info")
    liq_score = max(0, min(100, int(100 - max(0, top3_w - 20) * 2)))

    return [
        {
            "name": "Position Concentration", "severity": pos_sev, "score": pos_score,
            "metric":      f"{max_pos['ticker']} at {max_weight:.1f}%",
            "description": (
                f"Largest holding is {max_pos['ticker']} at {max_weight:.1f}% of portfolio. "
                f"Hard cap {_POS_CAP:.0f}%; target range {_POS_TARGET[0]:.0f}–{_POS_TARGET[1]:.0f}%."
            ),
            "limit":  f"Hard cap: {_POS_CAP:.0f}% per position · Target: {_POS_TARGET[0]:.0f}–{_POS_TARGET[1]:.0f}%",
            "action": (
                f"Trim {max_pos['ticker']} to target weight."
                if max_weight >= _POS_TARGET[1] else "All positions within acceptable range."
            ),
        },
        {
            "name": "Sector Concentration", "severity": sec_sev, "score": sec_score,
            "metric":      f"{max_sec} at {max_sec_pct:.1f}%",
            "description": (
                f"{max_sec} ({', '.join(sec_tickers)}) represents {max_sec_pct:.1f}% of portfolio. "
                f"{'Exceeds' if max_sec_pct >= _SECTOR_HARD else 'Approaching'} the {_SECTOR_HARD:.0f}% hard cap."
            ),
            "limit":  f"Soft target: {_SECTOR_SOFT:.0f}% · Hard cap: {_SECTOR_HARD:.0f}% per sector",
            "action": (
                f"No new {max_sec} positions until trimming is complete."
                if max_sec_pct >= _SECTOR_SOFT else "Sector allocation within acceptable range."
            ),
        },
        {
            "name": "Cash Level", "severity": cash_sev, "score": cash_score,
            "metric":      f"Cash at {cash_pct:.1f}%",
            "description": cash_desc,
            "limit":       f"Min: {_CASH_MIN:.0f}% · Target: {_CASH_TARGET:.0f}% · Max: {_CASH_MAX:.0f}%",
            "action":      cash_action,
        },
        {
            "name": "Portfolio Beta", "severity": beta_sev, "score": beta_score,
            "metric":      f"Beta {beta:.2f}",
            "description": (
                f"Portfolio beta of {beta:.2f} means it will {beta_dir} market moves by "
                f"~{abs(beta - 1) * 100:.0f}%. Target range is {_BETA_TARGET[0]:.1f}–{_BETA_TARGET[1]:.1f}. "
                f"(Stored value — live beta requires historical return data.)"
            ),
            "limit":  f"Target: {_BETA_TARGET[0]:.1f}–{_BETA_TARGET[1]:.1f} · Alert above: {_BETA_ALERT:.1f}",
            "action": (
                "Add defensive low-beta positions to reduce market sensitivity."
                if beta > _BETA_TARGET[1] else "Portfolio beta within target range."
            ),
        },
        {
            "name": "Overvaluation Risk", "severity": ov_sev, "score": ov_score,
            "metric":      f"{n_ov} position{'s' if n_ov != 1 else ''} above fair value",
            "description": ov_desc,
            "limit":       "No position > 40% above fair value · Avoid adding to overvalued names",
            "action":      ov_action,
        },
        {
            "name": "Drawdown & Liquidity", "severity": liq_sev, "score": liq_score,
            "metric":      f"Top 3 at {top3_w:.1f}% combined",
            "description": (
                f"Top 3 holdings ({top3_tix}) represent {top3_w:.1f}% of portfolio. "
                f"{'Within' if top3_w <= 30 else 'Exceeds'} the 30% combined concentration limit."
            ),
            "limit":  "Top 3 combined ≤ 30% · All holdings are exchange-listed large-caps",
            "action": (
                "Trim top positions to reduce concentration."
                if top3_w > 30 else "Concentration within acceptable range."
            ),
        },
    ]


def _build_risk_alerts(holdings: list, sector_weights: dict, cash_pct: float) -> list:
    """
    Auto-generate risk alerts from live portfolio metrics.
    Ported from risk_centre.py._build_risk_alerts().
    """
    alerts = []

    for h in sorted(holdings, key=lambda h: h.get("weight", 0), reverse=True):
        w = h.get("weight", 0)
        if w >= _POS_CAP:
            alerts.append({
                "severity": "high", "title": f"{h['ticker']} Hard Cap Breach",
                "description": f"{h['ticker']} at {w:.1f}% — exceeds {_POS_CAP:.0f}% hard cap. Trim immediately.",
            })
        elif w >= _POS_TARGET[1]:
            alerts.append({
                "severity": "medium", "title": f"{h['ticker']} Overweight",
                "description": f"{h['ticker']} at {w:.1f}% — above {_POS_TARGET[1]:.0f}% target. Plan to trim.",
            })

    for sector, pct in sorted(sector_weights.items(), key=lambda x: -x[1]):
        if pct >= _SECTOR_HARD:
            alerts.append({
                "severity": "high", "title": f"{sector} Sector Hard Cap",
                "description": f"{sector} at {pct:.1f}% — exceeds {_SECTOR_HARD:.0f}% hard cap.",
            })
        elif pct >= _SECTOR_SOFT:
            alerts.append({
                "severity": "medium", "title": f"{sector} Sector Warning",
                "description": f"{sector} at {pct:.1f}% — approaching limit. No new {sector} buys.",
            })

    if cash_pct < _CASH_MIN:
        alerts.append({
            "severity": "high", "title": "Insufficient Cash",
            "description": f"Cash at {cash_pct:.1f}% — below {_CASH_MIN:.0f}% minimum.",
        })
    elif cash_pct > _CASH_MAX:
        alerts.append({
            "severity": "medium", "title": "Excess Cash",
            "description": f"Cash at {cash_pct:.1f}% — above {_CASH_MAX:.0f}% maximum. Deploy into quality positions.",
        })

    for h in holdings:
        fv = _WL_FV.get(h["ticker"])
        if fv and h.get("current_price") and h["current_price"] > fv * 1.20:
            pct_above = (h["current_price"] / fv - 1) * 100
            alerts.append({
                "severity": "medium", "title": f"{h['ticker']} Above Fair Value",
                "description": f"{h['ticker']}: {pct_above:.0f}% above fair value estimate — avoid adding; consider trimming.",
            })

    if not alerts:
        alerts.append({
            "severity": "low", "title": "No Active Alerts",
            "description": "All monitored metrics are within acceptable ranges.",
        })

    return alerts


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
def get_portfolio():
    """
    Return live-enriched portfolio: holdings (with live prices), summary,
    and sector weights. Falls back to snapshot prices if the API is offline.
    """
    (
        holdings, sector_weights, total_value, total_invested,
        cash, cash_pct, daily_change_dollars, daily_change_pct, prices_live,
    ) = _build_live_portfolio()

    total_cost  = sum(h["cost_basis"]     for h in holdings)
    total_gain  = sum(h["unrealised_pnl"] for h in holdings)
    total_gain_pct = round(total_gain / total_cost * 100, 2) if total_cost else 0

    return {
        "summary": {
            "total_value":           round(total_value, 2),
            "invested":              round(total_invested, 2),
            "cash":                  round(cash, 2),
            "cash_pct":              cash_pct,
            "daily_change_dollars":  daily_change_dollars,
            "daily_change_pct":      daily_change_pct,
            "total_gain":            round(total_gain, 2),
            "total_gain_pct":        total_gain_pct,
            "num_holdings":          len(holdings),
            "health_score":          PORTFOLIO_SUMMARY.get("health_score", 70),
            "prices_live":           prices_live,
        },
        "holdings": [
            {
                "ticker":               h["ticker"],
                "name":                 h["name"],
                "sector":               h["sector"],
                "shares":               h["shares"],
                "avg_cost":             h["avg_cost"],
                "current_price":        h["current_price"],
                "market_value":         h["market_value"],
                "cost_basis":           h["cost_basis"],
                "unrealised_pnl":       h["unrealised_pnl"],
                "unrealised_pct":       h["unrealised_pct"],
                "daily_change_pct":     round(h.get("change_pct", 0), 4),
                "daily_change_dollars": h["daily_change_dollars"],
                "weight":               h["weight"],
            }
            for h in holdings
        ],
        "sector_weights": sector_weights,
    }


@router.get("/risk")
def get_portfolio_risk():
    """
    Compute and return live portfolio risk: 6 category cards, auto-generated
    alerts, and the overall health score. Ported from risk_centre.py.
    """
    (
        holdings, sector_weights, total_value, _, cash, cash_pct, _, _, prices_live,
    ) = _build_live_portfolio()

    categories   = _build_risk_categories(holdings, sector_weights, cash_pct)
    alerts       = _build_risk_alerts(holdings, sector_weights, cash_pct)

    criticals    = sum(1 for r in categories if r["severity"] == "critical")
    warnings_cnt = sum(1 for r in categories if r["severity"] == "warning")
    health_score = max(0, 100 - (warnings_cnt * 10) - (criticals * 20))

    top_pos = max(holdings, key=lambda h: h.get("weight", 0)) if holdings else {}

    return {
        "health_score": health_score,
        "categories":   categories,
        "alerts":       alerts,
        "sector_weights": sector_weights,
        "metrics": {
            "cash_pct":          cash_pct,
            "num_holdings":      len(holdings),
            "num_sectors":       len(sector_weights),
            "top_position":      top_pos.get("ticker", ""),
            "top_position_pct":  top_pos.get("weight", 0),
            "portfolio_beta":    PORTFOLIO_SUMMARY.get("portfolio_beta", 1.0),
        },
        "prices_live": prices_live,
    }


@router.get("/performance")
def get_performance(period: str = Query("3m", regex="^(1m|3m|6m|1y)$")):
    """
    Reconstruct historical NAV with accuracy across all periods.

    If Sharesight trade history is available, the portfolio composition is
    evolved day-by-day as trades occur — so 3M/1Y reflect what you actually
    held, not just today's positions applied backwards.

    Falls back to current-holdings × candle-prices when Sharesight is offline.
    """
    import logging
    log = logging.getLogger(__name__)

    base_holdings = _get_base_holdings()
    cash_balance  = PORTFOLIO_SUMMARY.get("cash", 0.0)

    # ── Try to fetch Sharesight trade history ─────────────────────────────────
    sharesight_trades: list[dict] = []
    try:
        import providers.sharesight_provider as sharesight
        from config.api_keys import SHARESIGHT_ACCESS_TOKEN
        if SHARESIGHT_ACCESS_TOKEN:
            sharesight_trades = sharesight.get_trades() or []
    except Exception as exc:
        log.warning(f"Sharesight trades unavailable, using current holdings: {exc}")

    # Tickers to fetch candles for: current holdings ∪ any ticker ever traded ∪ SPY
    current_tickers = {h["ticker"] for h in base_holdings}
    trade_tickers   = {t["ticker"] for t in sharesight_trades}
    all_tickers     = current_tickers | trade_tickers | {"SPY"}

    # ── Fetch candles in parallel ─────────────────────────────────────────────
    candle_map: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=min(len(all_tickers), 12)) as pool:
        futures = {
            pool.submit(market_data_service.get_candles, tk, period): tk
            for tk in all_tickers
        }
        for future in as_completed(futures, timeout=35):
            tk = futures[future]
            try:    candle_map[tk] = future.result() or []
            except: candle_map[tk] = []

    spy_candles = candle_map.pop("SPY", [])
    spy_by_date: dict[str, float] = {
        c["date"]: c["close"] for c in spy_candles if c.get("date") and c.get("close")
    }

    # Build {ticker: {date: close}} price maps
    ticker_prices: dict[str, dict[str, float]] = {}
    all_dates: set[str] = set()
    for tk, candles in candle_map.items():
        by_date = {c["date"]: c["close"] for c in candles if c.get("date") and c.get("close")}
        ticker_prices[tk] = by_date
        all_dates.update(by_date.keys())

    sorted_dates = sorted(all_dates)
    if not sorted_dates:
        return {"series": [], "period": period, "change_pct": 0.0, "change_dollars": 0.0,
                "benchmark_change_pct": None}

    # Carry-forward price state
    last_price: dict[str, float] = {}
    last_spy: float | None = spy_by_date.get(min(spy_by_date)) if spy_by_date else None

    series: list[dict] = []

    if sharesight_trades:
        # ── Trade-aware path: evolve holdings as buys/sells occur ────────────
        running_holdings: dict[str, float] = {}   # {ticker: shares}
        sorted_trades = sorted(sharesight_trades, key=lambda x: x["date"])
        trade_idx = 0

        for date in sorted_dates:
            # Apply every trade that falls on or before this date
            while trade_idx < len(sorted_trades) and sorted_trades[trade_idx]["date"] <= date:
                tr    = sorted_trades[trade_idx]
                tk    = tr["ticker"]
                qty   = tr["quantity"]
                ttype = tr["type"]
                if ttype in ("BUY", "ACCUMULATE", "TRANSFER_IN"):
                    running_holdings[tk] = running_holdings.get(tk, 0) + qty
                elif ttype in ("SELL", "REDUCE", "TRANSFER_OUT"):
                    new_qty = running_holdings.get(tk, 0) - qty
                    running_holdings[tk] = max(new_qty, 0)
                    if running_holdings[tk] == 0:
                        running_holdings.pop(tk, None)
                trade_idx += 1

            # Update carry-forward prices for held tickers
            for tk in running_holdings:
                if date in ticker_prices.get(tk, {}):
                    last_price[tk] = ticker_prices[tk][date]
            if date in spy_by_date:
                last_spy = spy_by_date[date]

            day_value = cash_balance + sum(
                last_price.get(tk, 0) * shares
                for tk, shares in running_holdings.items()
                if last_price.get(tk)
            )
            series.append({
                "date":      date,
                "value":     round(day_value, 2),
                "spy_close": round(last_spy, 4) if last_spy else None,
            })

    else:
        # ── Fallback: current holdings held for full period ───────────────────
        holdings_meta = [{"ticker": h["ticker"], "shares": h["shares"]} for h in base_holdings]

        # Seed carry-forward from each ticker's earliest available price
        for h in holdings_meta:
            tk    = h["ticker"]
            dates = sorted(ticker_prices.get(tk, {}).keys())
            if dates:
                last_price[tk] = ticker_prices[tk][dates[0]]

        for date in sorted_dates:
            for h in holdings_meta:
                tk = h["ticker"]
                if date in ticker_prices.get(tk, {}):
                    last_price[tk] = ticker_prices[tk][date]
            if date in spy_by_date:
                last_spy = spy_by_date[date]

            day_value = cash_balance + sum(
                last_price.get(h["ticker"], 0) * h["shares"]
                for h in holdings_meta
                if last_price.get(h["ticker"])
            )
            series.append({
                "date":      date,
                "value":     round(day_value, 2),
                "spy_close": round(last_spy, 4) if last_spy else None,
            })

    # ── Compute period stats ──────────────────────────────────────────────────
    start = series[0]["value"]
    end   = series[-1]["value"]
    change_dollars = round(end - start, 2)
    change_pct     = round((end - start) / start * 100, 2) if start else 0.0

    # Normalise SPY to portfolio starting value for overlay comparison
    spy_start = series[0].get("spy_close")
    spy_end   = series[-1].get("spy_close")
    if spy_start and spy_end and spy_start > 0:
        scale = start / spy_start
        for pt in series:
            pt["benchmark"] = round(pt["spy_close"] * scale, 2) if pt["spy_close"] else None
        benchmark_change_pct = round((spy_end - spy_start) / spy_start * 100, 2)
    else:
        for pt in series:
            pt["benchmark"] = None
        benchmark_change_pct = None

    return {
        "series":               series,
        "period":               period,
        "start_value":          round(start, 2),
        "end_value":            round(end, 2),
        "change_pct":           change_pct,
        "change_dollars":       change_dollars,
        "benchmark_change_pct": benchmark_change_pct,
    }


@router.get("/decisions")
def get_decisions():
    """
    Generate rule-based signals (ADD/HOLD/MONITOR/TRIM) from live portfolio metrics.
    Signals are derived from unrealised gains, position weights, daily moves, and cash level.
    """
    (
        holdings, _, _, _, cash, cash_pct, _, _, prices_live,
    ) = _build_live_portfolio()

    signals = []

    # Cash above max threshold → deploy into watchlist positions
    if cash_pct > _CASH_MAX:
        signals.append({
            "ticker":  "CASH",
            "action":  "ADD",
            "reason":  f"Cash at {cash_pct:.1f}% — above {_CASH_MAX:.0f}% max. Add to rated watchlist positions.",
            "urgency": "medium",
        })

    for h in sorted(holdings, key=lambda h: h.get("unrealised_pct", 0), reverse=True):
        ticker  = h["ticker"]
        unr_pct = h.get("unrealised_pct", 0)
        weight  = h.get("weight", 0)
        daily   = h.get("change_pct", 0)
        fv      = _WL_FV.get(ticker)

        # Above fair value from watchlist → TRIM
        if fv and h.get("current_price") and h["current_price"] > fv * 1.15:
            pct_above = (h["current_price"] / fv - 1) * 100
            signals.append({
                "ticker":  ticker,
                "action":  "TRIM",
                "reason":  f"{pct_above:.0f}% above fair value estimate. Consider trimming to lock in gains.",
                "urgency": "high",
            })
        # Large unrealised gain at meaningful weight → TRIM candidate
        elif unr_pct > 50 and weight >= 4.0:
            signals.append({
                "ticker":  ticker,
                "action":  "TRIM",
                "reason":  f"+{unr_pct:.0f}% unrealised gain at {weight:.1f}% weight. Consider partial trim.",
                "urgency": "high",
            })
        # Strong gain, lighter weight → MONITOR for drift
        elif unr_pct > 25 and weight >= 4.0:
            signals.append({
                "ticker":  ticker,
                "action":  "MONITOR",
                "reason":  f"+{unr_pct:.0f}% unrealised gain. Watch for trim opportunity if weight drifts up.",
                "urgency": "medium",
            })
        # Underwater position at small weight → ADD opportunistically
        elif unr_pct < -15 and weight < 5.0:
            signals.append({
                "ticker":  ticker,
                "action":  "ADD",
                "reason":  f"{unr_pct:.0f}% unrealised loss. Opportunistic add if thesis is intact.",
                "urgency": "medium",
            })
        # Significant daily drop → check for news
        elif daily < -2.5:
            signals.append({
                "ticker":  ticker,
                "action":  "MONITOR",
                "reason":  f"Down {abs(daily):.1f}% today. Check for news catalyst before acting.",
                "urgency": "low",
            })

    if not signals:
        signals.append({
            "ticker":  "PORTFOLIO",
            "action":  "HOLD",
            "reason":  "All positions within acceptable ranges. No immediate action required.",
            "urgency": "low",
        })

    urgency_order = {"high": 0, "medium": 1, "low": 2}
    signals.sort(key=lambda s: urgency_order.get(s["urgency"], 3))

    return {"decisions": signals[:5], "prices_live": prices_live}


@router.get("/opportunities")
def get_opportunities():
    """
    Return top watchlist opportunities ranked by upside to fair value.
    Only returns tickers with a researched fair value and score.
    """
    candidates = [
        w for w in WATCHLIST
        if w.get("fair_value", 0) > 0 and w.get("final_score", 0) > 0
    ]

    if not candidates:
        return {"opportunities": []}

    tickers     = [c["ticker"] for c in candidates]
    live_prices = market_data_service.get_portfolio_prices(tickers) or {}

    opps = []
    for w in candidates:
        ticker    = w["ticker"]
        fv        = w["fair_value"]
        buy_below = w.get("buy_below", fv * 0.80)
        live      = live_prices.get(ticker) or {}
        price     = live.get("price") or w.get("price") or 0.0

        if not price or not fv:
            continue

        upside_pct = round((fv - price) / price * 100, 1)

        if price <= buy_below:
            tag = "Buy Zone"
        elif price < fv:
            tag = "Below Fair Value"
        else:
            tag = "Near Fair Value"

        opps.append({
            "ticker":     ticker,
            "company":    w["name"],
            "price":      round(price, 2),
            "fair_value": round(fv, 2),
            "upside":     upside_pct,
            "score":      w.get("final_score", 0),
            "tag":        tag,
        })

    opps.sort(key=lambda o: -o["upside"])
    return {"opportunities": opps[:5]}


@router.get("/dividends")
def get_dividends():
    """
    Return upcoming ex-dividend and payment dates for portfolio holdings.
    Uses yfinance .info (has exDividendDate / dividendDate Unix timestamps).
    Runs all tickers in parallel; skips non-dividend-paying stocks.
    """
    import yfinance as yf
    from datetime import datetime, timezone, date

    base_holdings  = _get_base_holdings()
    holding_map    = {h["ticker"]: h.get("name", h["ticker"]) for h in base_holdings}

    # Also include dividend-paying watchlist stocks not already in the portfolio
    from utils.sample_data import WATCHLIST
    extra_tickers = [
        w["ticker"] for w in WATCHLIST
        if w["ticker"] not in holding_map
        and w.get("sector") in ("Consumer Staples", "Real Estate", "Financials", "Healthcare", "Utilities")
    ]
    all_tickers = list(holding_map.keys()) + extra_tickers[:15]

    def _fetch_one(ticker: str) -> dict | None:
        try:
            info = yf.Ticker(ticker).info
            div_rate  = info.get("dividendRate") or info.get("trailingAnnualDividendRate") or 0
            div_yield = info.get("dividendYield") or info.get("trailingAnnualDividendYield") or 0
            if not div_rate:
                return None

            def _ts(val) -> str | None:
                if not val:
                    return None
                try:
                    return datetime.fromtimestamp(int(val), tz=timezone.utc).strftime("%Y-%m-%d")
                except Exception:
                    return None

            ex_div  = _ts(info.get("exDividendDate"))
            pay_day = _ts(info.get("dividendDate"))
            name    = info.get("longName") or info.get("shortName") or holding_map.get(ticker, ticker)

            return {
                "ticker":        ticker,
                "name":          name,
                "ex_div_date":   ex_div,
                "pay_date":      pay_day,
                "annual_div":    round(div_rate, 4),
                "quarterly_div": round(div_rate / 4, 4),
                "yield_pct":     round(div_yield * 100, 2) if div_yield else None,
                "in_portfolio":  ticker in holding_map,
            }
        except Exception:
            return None

    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        future_map = {pool.submit(_fetch_one, t): t for t in all_tickers}
        for future in as_completed(future_map, timeout=45):
            try:
                r = future.result()
                if r:
                    results.append(r)
            except Exception:
                pass

    today = date.today().isoformat()
    upcoming = sorted(
        [r for r in results if r.get("ex_div_date") and r["ex_div_date"] >= today],
        key=lambda r: r["ex_div_date"],
    )
    recent = sorted(
        [r for r in results if not r.get("ex_div_date") or r["ex_div_date"] < today],
        key=lambda r: r.get("ex_div_date") or "0000",
        reverse=True,
    )

    return {"upcoming": upcoming[:15], "recent": recent[:10]}
