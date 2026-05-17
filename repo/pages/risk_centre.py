"""
risk_centre.py — Risk Centre page (Stage 4 — live data).

Fetches live portfolio prices and computes all risk metrics dynamically.
Static data (shares, avg_cost, target_weight) comes from sample_data — the
investor's own records. Everything else (weights, concentrations, alerts)
is re-derived from live prices every time the page loads.
"""

import streamlit as st
from datetime import datetime

from components import (
    render_section_header,
    render_metric_card,
    render_risk_alert,
    html_badge,
    render_html,
    now_str,
)
from utils.sample_data import PORTFOLIO_HOLDINGS, PORTFOLIO_SUMMARY, WATCHLIST
from services import market_data_service

# Fair-value lookup from watchlist — used for overvaluation checks
_WL_FV = {s["ticker"]: s.get("fair_value") for s in WATCHLIST}

# Risk limits
_POS_CAP     = 10.0
_POS_TARGET  = (4.0, 8.0)
_SECTOR_SOFT = 25.0
_SECTOR_HARD = 30.0
_CASH_MIN    = 5.0
_CASH_TARGET = 10.0
_CASH_MAX    = 20.0
_BETA_TARGET = (0.8, 1.2)
_BETA_ALERT  = 1.3

_SEVERITY_CONFIG = {
    "info":     ("#eff6ff", "#bfdbfe", "#1e40af", "ℹ️"),
    "warning":  ("#fffbeb", "#fde68a", "#92400e", "⚠️"),
    "critical": ("#fef2f2", "#fecaca", "#991b1b", "🚨"),
}


# ── Data layer ─────────────────────────────────────────────────────────────────

def _build_live_portfolio() -> tuple[list, dict, float, float, bool]:
    """
    Fetch live prices and recompute per-holding and portfolio-level metrics.
    Returns (holdings, sector_weights, cash_pct, total_value, prices_live).
    """
    tickers     = [h["ticker"] for h in PORTFOLIO_HOLDINGS]
    live_prices = market_data_service.get_portfolio_prices(tickers)
    prices_live = False

    holdings = []
    for h in PORTFOLIO_HOLDINGS:
        item       = h.copy()
        price_data = live_prices.get(h["ticker"])
        if price_data and price_data.get("price"):
            item["current_price"] = price_data["price"]
            item["change_pct"]    = price_data.get("change_pct", 0) or 0
            prices_live = True
        item["market_value"] = item["current_price"] * item["shares"]
        holdings.append(item)

    total_invested = sum(h["market_value"] for h in holdings)
    cash           = PORTFOLIO_SUMMARY["cash"]
    total_value    = total_invested + cash

    for item in holdings:
        item["current_weight"] = (item["market_value"] / total_value * 100) if total_value else 0

    sector_weights: dict[str, float] = {}
    for item in holdings:
        s = item["sector"]
        sector_weights[s] = round(sector_weights.get(s, 0) + item["current_weight"], 2)

    cash_pct = cash / total_value * 100 if total_value else 0

    return holdings, sector_weights, cash_pct, total_value, prices_live


def _build_risk_categories(holdings: list, sector_weights: dict, cash_pct: float) -> list:
    """Compute 6 risk category cards from live portfolio metrics."""

    # 1. Position Concentration
    max_pos    = max(holdings, key=lambda h: h.get("current_weight", 0))
    max_weight = max_pos.get("current_weight", 0)
    pos_sev    = ("critical" if max_weight >= _POS_CAP
                  else "warning" if max_weight >= _POS_TARGET[1] else "info")
    pos_score  = max(0, min(100, int(100 - max(0, max_weight - _POS_TARGET[0]) * 8)))

    # 2. Sector Concentration
    max_sec     = max(sector_weights, key=sector_weights.get)
    max_sec_pct = sector_weights[max_sec]
    sec_sev     = ("critical" if max_sec_pct >= _SECTOR_HARD
                   else "warning" if max_sec_pct >= _SECTOR_SOFT else "info")
    sec_score   = max(0, min(100, int(100 - max(0, max_sec_pct - 20) * 4)))
    sec_tickers = [h["ticker"] for h in holdings if h["sector"] == max_sec]

    # 3. Cash Level
    dist        = abs(cash_pct - _CASH_TARGET)
    cash_sev    = ("critical" if cash_pct < _CASH_MIN or cash_pct > _CASH_MAX
                   else "warning" if dist > 4 else "info")
    cash_score  = max(0, min(100, int(100 - dist * 5)))
    if cash_pct < _CASH_MIN:
        cash_desc   = f"Cash at {cash_pct:.1f}% — below minimum. Insufficient dry powder for opportunities."
        cash_action = "Raise cash by trimming overweight positions before buying anything new."
    elif cash_pct > _CASH_MAX:
        cash_desc   = f"Cash at {cash_pct:.1f}% — above maximum. Too much idle capital."
        cash_action = "Deploy into rated Buy/Add positions from the watchlist."
    else:
        cash_desc   = f"Cash at {cash_pct:.1f}% — within the {_CASH_MIN:.0f}–{_CASH_MAX:.0f}% target band."
        cash_action = ("Maintain current cash level." if dist < 2
                       else "Monitor and rebalance as trades execute.")

    # 4. Portfolio Beta (stored value — requires historical data to compute live)
    beta       = PORTFOLIO_SUMMARY.get("portfolio_beta", 1.0)
    beta_ok    = _BETA_TARGET[0] <= beta <= _BETA_TARGET[1]
    beta_sev   = ("critical" if beta > _BETA_ALERT or beta < 0.5
                  else "warning" if not beta_ok else "info")
    beta_score = max(0, min(100, int(100 - abs(beta - 1.0) * 40)))
    beta_dir   = "amplify" if beta > 1 else "dampen"

    # 5. Overvaluation Risk
    overvalued = []
    for h in holdings:
        fv = _WL_FV.get(h["ticker"])
        if fv and h.get("current_price") and h["current_price"] > fv:
            overvalued.append((h["ticker"], (h["current_price"] / fv - 1) * 100))
    overvalued.sort(key=lambda x: -x[1])
    n_ov    = len(overvalued)
    ov_sev  = "critical" if n_ov >= 4 else ("warning" if n_ov >= 2 else "info")
    ov_score = max(0, min(100, int(100 - n_ov * 12)))
    if overvalued:
        ov_tickers = ", ".join(f"{t} (+{p:.0f}%)" for t, p in overvalued[:3])
        ov_desc    = f"{n_ov} holding{'s' if n_ov > 1 else ''} above fair value: {ov_tickers}."
        ov_action  = "Do not add to overvalued positions. Consider trimming if significantly above fair value."
    else:
        ov_desc   = "All holdings are at or below estimated fair value — good upside remaining."
        ov_action = "Continue adding to positions within buy range per the watchlist plan."

    # 6. Drawdown & Liquidity — top-3 weight
    sorted_h = sorted(holdings, key=lambda h: h.get("current_weight", 0), reverse=True)
    top3_w   = sum(h.get("current_weight", 0) for h in sorted_h[:3])
    top3_tix = ", ".join(h["ticker"] for h in sorted_h[:3])
    liq_sev  = "critical" if top3_w > 40 else ("warning" if top3_w > 30 else "info")
    liq_score = max(0, min(100, int(100 - max(0, top3_w - 20) * 2)))

    return [
        {
            "name": "Position Concentration", "icon": "🏦",
            "severity": pos_sev, "score": pos_score,
            "metric":      f"{max_pos['ticker']} at {max_weight:.1f}%",
            "description": (f"Largest single holding is {max_pos['ticker']} at {max_weight:.1f}% of portfolio. "
                            f"Hard cap is {_POS_CAP:.0f}%; target range is {_POS_TARGET[0]:.0f}–{_POS_TARGET[1]:.0f}%."),
            "limit":  f"Hard cap: {_POS_CAP:.0f}% per position · Target: {_POS_TARGET[0]:.0f}–{_POS_TARGET[1]:.0f}%",
            "action": (f"Trim {max_pos['ticker']} to target weight per rebalance plan."
                       if max_weight >= _POS_TARGET[1] else "All positions within acceptable range."),
        },
        {
            "name": "Sector Concentration", "icon": "🗂️",
            "severity": sec_sev, "score": sec_score,
            "metric":      f"{max_sec} at {max_sec_pct:.1f}%",
            "description": (f"{max_sec} ({', '.join(sec_tickers)}) represents {max_sec_pct:.1f}% of portfolio. "
                            f"{'Approaching' if max_sec_pct < _SECTOR_HARD else 'Exceeds'} the {_SECTOR_HARD:.0f}% hard cap."),
            "limit":  f"Soft target: {_SECTOR_SOFT:.0f}% · Hard cap: {_SECTOR_HARD:.0f}% per sector",
            "action": (f"No new {max_sec} positions until trimming is complete."
                       if max_sec_pct >= _SECTOR_SOFT else "Sector allocation within acceptable range."),
        },
        {
            "name": "Cash Level", "icon": "💵",
            "severity": cash_sev, "score": cash_score,
            "metric":      f"Cash at {cash_pct:.1f}%",
            "description": cash_desc,
            "limit":       f"Min: {_CASH_MIN:.0f}% · Target: {_CASH_TARGET:.0f}% · Max: {_CASH_MAX:.0f}%",
            "action":      cash_action,
        },
        {
            "name": "Portfolio Beta", "icon": "📊",
            "severity": beta_sev, "score": beta_score,
            "metric":      f"Beta {beta:.2f}",
            "description": (f"Portfolio beta of {beta:.2f} means it will {beta_dir} market moves by "
                            f"~{abs(beta - 1) * 100:.0f}%. Target range is {_BETA_TARGET[0]:.1f}–{_BETA_TARGET[1]:.1f}. "
                            f"(Beta is a stored value — requires historical returns to compute live.)"),
            "limit":  f"Target: {_BETA_TARGET[0]:.1f}–{_BETA_TARGET[1]:.1f} · Alert above: {_BETA_ALERT:.1f}",
            "action": ("Add defensive low-beta positions to reduce market sensitivity."
                       if beta > _BETA_TARGET[1] else "Portfolio beta within target range."),
        },
        {
            "name": "Overvaluation Risk", "icon": "📈",
            "severity": ov_sev, "score": ov_score,
            "metric":      f"{n_ov} position{'s' if n_ov != 1 else ''} above fair value",
            "description": ov_desc,
            "limit":       "No position > 40% above fair value · Avoid adding to overvalued names",
            "action":      ov_action,
        },
        {
            "name": "Drawdown & Liquidity", "icon": "📉",
            "severity": liq_sev, "score": liq_score,
            "metric":      f"Top 3 at {top3_w:.1f}% combined",
            "description": (f"Top 3 holdings ({top3_tix}) represent {top3_w:.1f}% of portfolio. "
                            f"{'Within' if top3_w <= 30 else 'Exceeds'} the 30% combined concentration limit."),
            "limit":  "Top 3 combined ≤ 30% · All holdings are exchange-listed large-caps",
            "action": ("Trim top positions to reduce concentration." if top3_w > 30
                       else "Concentration within acceptable range."),
        },
    ]


def _build_risk_alerts(holdings: list, sector_weights: dict, cash_pct: float) -> list:
    """Auto-generate risk alerts from live portfolio metrics."""
    alerts = []

    for h in sorted(holdings, key=lambda h: h.get("current_weight", 0), reverse=True):
        w = h.get("current_weight", 0)
        if w >= _POS_CAP:
            alerts.append({"level": "danger",
                           "message": f"{h['ticker']}: position at {w:.1f}% — exceeds {_POS_CAP:.0f}% hard cap. Trim immediately."})
        elif w >= _POS_TARGET[1]:
            alerts.append({"level": "warning",
                           "message": f"{h['ticker']}: position at {w:.1f}% — above {_POS_TARGET[1]:.0f}% target. Plan to trim."})

    for sector, pct in sorted(sector_weights.items(), key=lambda x: -x[1]):
        if pct >= _SECTOR_HARD:
            alerts.append({"level": "danger",
                           "message": f"{sector} sector at {pct:.1f}% — exceeds {_SECTOR_HARD:.0f}% hard cap."})
        elif pct >= _SECTOR_SOFT:
            alerts.append({"level": "warning",
                           "message": f"{sector} sector at {pct:.1f}% — approaching {_SECTOR_HARD:.0f}% limit. No new {sector} buys."})

    if cash_pct < _CASH_MIN:
        alerts.append({"level": "danger",
                       "message": f"Cash at {cash_pct:.1f}% — below {_CASH_MIN:.0f}% minimum. Cannot act on new opportunities."})
    elif cash_pct > _CASH_MAX:
        alerts.append({"level": "warning",
                       "message": f"Cash at {cash_pct:.1f}% — above {_CASH_MAX:.0f}% maximum. Idle capital is a drag on returns."})

    beta = PORTFOLIO_SUMMARY.get("portfolio_beta", 1.0)
    if beta > _BETA_ALERT:
        alerts.append({"level": "warning",
                       "message": f"Portfolio beta {beta:.2f} — above {_BETA_ALERT:.1f} alert threshold. Portfolio will amplify market drawdowns."})

    for h in holdings:
        fv = _WL_FV.get(h["ticker"])
        if fv and h.get("current_price") and h["current_price"] > fv * 1.20:
            pct_above = (h["current_price"] / fv - 1) * 100
            alerts.append({"level": "warning",
                           "message": f"{h['ticker']}: {pct_above:.0f}% above fair value estimate — avoid adding; consider trimming."})

    if not alerts:
        alerts.append({"level": "info",
                       "message": "No active risk alerts — all monitored metrics are within acceptable ranges."})

    return alerts


# ── Page sections ──────────────────────────────────────────────────────────────

def render():
    _header()

    with st.spinner("Loading live portfolio risk data…"):
        holdings, sector_weights, cash_pct, total_value, prices_live = _build_live_portfolio()

    if not prices_live:
        st.warning("Live prices unavailable — risk metrics based on last known prices. Check API connection.")

    risk_categories = _build_risk_categories(holdings, sector_weights, cash_pct)
    risk_alerts     = _build_risk_alerts(holdings, sector_weights, cash_pct)

    _overall_score(risk_categories)
    st.markdown("<br>", unsafe_allow_html=True)
    _risk_grid(risk_categories)
    st.markdown("<br>", unsafe_allow_html=True)
    _active_alerts(risk_alerts)
    st.markdown("<br>", unsafe_allow_html=True)
    _legend()


def _header():
    col_title, col_meta = st.columns([5, 1])
    with col_title:
        render_html(
            f'<div style="margin-bottom:4px;">'
            f'<span style="font-size:22px; font-weight:700; color:#0B0B0F; letter-spacing:-0.02em;">Risk Centre</span>'
            f'</div>'
            f'<div style="font-size:13px; color:#5B6472;">'
            f'Live portfolio risk — concentration, beta, sector, and valuation risk'
            f' · {datetime.now().strftime("%d %B %Y")}</div>'
        )
    with col_meta:
        render_html(
            f'<div style="padding-top:14px; text-align:right; font-size:11px; color:#94a3b8;">Updated {now_str()}</div>'
        )
    st.markdown('<div style="height:1px; background:#e2e8f0; margin:14px 0 20px;"></div>', unsafe_allow_html=True)


def _overall_score(categories: list):
    criticals    = sum(1 for r in categories if r["severity"] == "critical")
    warnings     = sum(1 for r in categories if r["severity"] == "warning")
    infos        = sum(1 for r in categories if r["severity"] == "info")
    overall      = max(0, 100 - (warnings * 10) - (criticals * 20))
    overall_type = "positive" if overall >= 70 else ("neutral" if overall >= 50 else "negative")

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        render_metric_card(label="Risk Score", value=f"{overall}/100",
            delta="Higher = safer", delta_type=overall_type, icon="🛡️", accent=True)
    with c2:
        render_metric_card(label="Critical Issues", value=str(criticals),
            delta="immediate action" if criticals else "none active",
            delta_type="negative" if criticals else "positive", icon="🚨")
    with c3:
        render_metric_card(label="Warnings", value=str(warnings),
            delta="monitor closely",
            delta_type="negative" if warnings > 2 else "neutral", icon="⚠️")
    with c4:
        render_metric_card(label="Low Risk Items", value=str(infos),
            delta="no action needed", delta_type="positive", icon="✅")


def _risk_grid(categories: list):
    render_section_header(
        "Risk Categories",
        "Six monitored dimensions · green = low · amber = warning · red = critical",
        "🔍",
    )
    for row_start in range(0, len(categories), 3):
        cols = st.columns(3, gap="small")
        for col, risk in zip(cols, categories[row_start:row_start + 3]):
            with col:
                _risk_card(risk)
        st.markdown("<br>", unsafe_allow_html=True)


def _risk_card(risk: dict):
    bg, border, colour, icon = _SEVERITY_CONFIG.get(risk["severity"], _SEVERITY_CONFIG["info"])
    badge        = html_badge(risk["severity"].capitalize(), risk["severity"])
    score        = risk["score"]
    score_colour = "#10b981" if score >= 70 else ("#f59e0b" if score >= 50 else "#ef4444")

    render_html(
        f'<div style="background:{bg}; border:1px solid {border}; border-radius:12px; padding:18px; height:100%;">'
        f'<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">'
        f'<div style="display:flex; align-items:center; gap:8px;">'
        f'<span style="font-size:18px;">{icon}</span>'
        f'<span style="font-size:13px; font-weight:700; color:{colour};">{risk["name"]}</span>'
        f'</div>{badge}</div>'
        f'<div style="font-size:20px; font-weight:800; color:{colour}; letter-spacing:-0.02em; margin-bottom:6px;">{risk["metric"]}</div>'
        f'<div style="font-size:12px; color:{colour}; opacity:0.85; line-height:1.5; margin-bottom:10px;">{risk["description"]}</div>'
        f'<div style="font-size:10px; color:{colour}; opacity:0.6; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px; font-weight:600;">Limit</div>'
        f'<div style="font-size:11px; color:{colour}; opacity:0.75; margin-bottom:12px; font-style:italic;">{risk["limit"]}</div>'
        f'<div style="height:1px; background:{border}; margin-bottom:10px;"></div>'
        f'<div style="font-size:10px; color:{colour}; opacity:0.6; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px; font-weight:600;">Recommended Action</div>'
        f'<div style="font-size:12px; color:{colour}; font-weight:600; line-height:1.4;">{risk["action"]}</div>'
        f'<div style="margin-top:12px; display:flex; align-items:center; gap:8px;">'
        f'<span style="font-size:11px; color:{colour}; opacity:0.7;">Risk health:</span>'
        f'<span style="font-size:12px; font-weight:700; color:{score_colour};">{score}/100</span>'
        f'</div></div>'
    )


def _active_alerts(alerts: list):
    render_section_header("Active Portfolio Alerts", f"{len(alerts)} active", "⚠️")
    level_map  = {"warning": "warning", "danger": "critical", "info": "info"}
    action_map = {
        "danger":  "Immediate action required",
        "warning": "Monitor and plan action",
        "info":    "Awareness only",
    }
    for alert in alerts:
        raw = alert["level"]
        render_risk_alert(
            message            = alert["message"],
            level              = level_map.get(raw, "warning"),
            recommended_action = action_map.get(raw, ""),
        )


def _legend():
    render_section_header("Risk Scoring Guide", "", "📖")
    cols   = st.columns(3, gap="small")
    levels = [
        ("✅ Low Risk (score 70–100)",  "#f0fdf4", "#86efac", "#166534",
         "No action required. Risk is within acceptable parameters."),
        ("⚠️ Warning (score 50–69)",    "#fffbeb", "#fde68a", "#92400e",
         "Monitor closely. Plan a corrective action. Do not add to risk positions."),
        ("🚨 Critical (score 0–49)",    "#fef2f2", "#fca5a5", "#991b1b",
         "Immediate action required. Risk exceeds hard limits. Execute corrective trades promptly."),
    ]
    for col, (title, bg, border, colour, desc) in zip(cols, levels):
        with col:
            render_html(
                f'<div style="background:{bg}; border:1px solid {border}; border-radius:10px; padding:14px 16px;">'
                f'<div style="font-size:13px; font-weight:700; color:{colour}; margin-bottom:6px;">{title}</div>'
                f'<div style="font-size:12px; color:{colour}; opacity:0.85; line-height:1.45;">{desc}</div>'
                f'</div>'
            )
    st.markdown("<br>", unsafe_allow_html=True)
