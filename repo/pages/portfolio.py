"""
portfolio.py — Portfolio Dashboard (Stage 2 redesign).
"""

import streamlit as st
import pandas as pd
from datetime import datetime

try:
    import plotly.graph_objects as go
    _PLOTLY = True
except ImportError:
    import altair as alt
    _PLOTLY = False

from components import (
    render_section_header,
    render_risk_alert,
    render_html,
    now_str,
)
from utils.sample_data import PORTFOLIO_HOLDINGS, PORTFOLIO_SUMMARY, RISK_ALERTS
from utils.formatting import fmt_currency, fmt_pct, fmt_weight
from services import market_data_service

_ACTION_DISPLAY = {
    "Buy":  "🟢 Buy",   "Add":  "🔵 Add",   "Hold": "⚪ Hold",
    "Trim": "🟠 Trim",  "Sell": "🔴 Sell",   "Avoid": "⬛ Avoid",
}

_SECTOR_COLORS = {
    "Technology":             "#061A33",
    "Financials":             "#102A4C",
    "Consumer Staples":       "#183D6B",
    "Consumer Discretionary": "#1F4F87",
    "Communication Services": "#2864A4",
    "ETF":                    "#3479BC",
    "Real Estate":            "#4A8FD0",
    "Healthcare":             "#62A5E0",
    "Industrials":            "#7DBDE8",
    "Energy":                 "#99D0F0",
    "Utilities":              "#B5DFF8",
    "Materials":              "#CCDFEF",
    "Cash":                   "#94a3b8",
}


def _enrich_portfolio() -> tuple[list, dict, dict, bool]:
    """
    Fetch live prices and recalculate portfolio metrics.
    Returns (holdings, summary, sector_exposure, prices_live).
    """
    tickers     = [h["ticker"] for h in PORTFOLIO_HOLDINGS]
    live_prices = market_data_service.get_portfolio_prices(tickers)
    prices_live = False
    daily_pnl   = 0.0

    holdings = []
    for h in PORTFOLIO_HOLDINGS:
        item           = h.copy()
        item["change_pct"] = 0.0
        price_data     = live_prices.get(h["ticker"])
        if price_data and price_data.get("price"):
            live_price            = price_data["price"]
            item["current_price"] = live_price
            item["market_value"]  = round(live_price * h["shares"], 2)
            prices_live           = True
            change_pct            = price_data.get("change_pct", 0) or 0
            item["change_pct"]    = change_pct
            daily_pnl            += item["market_value"] * change_pct
        holdings.append(item)

    total_invested = sum(h["market_value"] for h in holdings)
    cash           = PORTFOLIO_SUMMARY["cash"]
    total_value    = total_invested + cash

    for item in holdings:
        item["current_weight"] = round(item["market_value"] / total_value * 100, 2) if total_value else 0

    sector_exposure: dict[str, float] = {}
    for item in holdings:
        s = item["sector"]
        sector_exposure[s] = round(sector_exposure.get(s, 0) + item["current_weight"], 1)
    sector_exposure["Cash"] = round(cash / total_value * 100, 1) if total_value else 0

    summary = PORTFOLIO_SUMMARY.copy()
    summary["total_value"]          = round(total_value, 2)
    summary["invested"]             = round(total_invested, 2)
    summary["cash_pct"]             = round(cash / total_value, 4) if total_value else 0
    summary["num_holdings"]         = len(holdings)
    summary["daily_change_dollars"] = round(daily_pnl, 2)
    summary["daily_change_pct"]     = round(daily_pnl / (total_value - daily_pnl), 4) if total_value else 0

    return holdings, summary, sector_exposure, prices_live


def render():
    holdings, summary, sector_exposure, prices_live = _enrich_portfolio()
    if not prices_live:
        st.warning("Live prices unavailable — showing last known values. Check API connection.")

    _header()

    # Hero: stats panel left, donut chart right
    col_stats, col_chart = st.columns([2, 3], gap="large")
    with col_stats:
        _summary_metrics(summary, holdings)
    with col_chart:
        _sector_chart(sector_exposure)

    st.markdown("<br>", unsafe_allow_html=True)
    _rebalance_table(holdings)
    st.markdown("<br>", unsafe_allow_html=True)

    col_trade, col_conc = st.columns([3, 2], gap="large")
    with col_trade:
        _trade_summary(holdings)
    with col_conc:
        _concentration_panel(holdings)

    st.markdown("<br>", unsafe_allow_html=True)
    _risk_warnings()


# ── Sections ──────────────────────────────────────────────────────────────────

def _header():
    render_html(
        f'<div style="margin-bottom:4px;">'
        f'<span style="font-size:22px;font-weight:700;color:#0B0B0F;letter-spacing:-0.02em;">Portfolio</span>'
        f'</div>'
        f'<div style="font-size:13px;color:#5B6472;">'
        f'Holdings, allocation, and rebalance plan · {datetime.now().strftime("%d %B %Y")}'
        f'</div>'
    )
    st.markdown('<div style="height:1px;background:#E2E8F0;margin:14px 0 20px;"></div>', unsafe_allow_html=True)


def _summary_metrics(p: dict, holdings: list):
    """Left-side hero stat panel."""
    daily_up    = p["daily_change_pct"] >= 0
    daily_icon  = "▲" if daily_up else "▼"
    daily_color = "#16A34A" if daily_up else "#DC2626"

    trims = sum(1 for h in holdings if h.get("trade_dir") == "Sell")
    buys  = sum(1 for h in holdings if h.get("trade_dir") == "Buy")
    if trims or buys:
        rebal_text  = f"{buys} add · {trims} trim pending"
        rebal_color = "#B45309"
    else:
        rebal_text  = "Portfolio on target ✓"
        rebal_color = "#16A34A"

    render_html(
        f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;'
        f'padding:28px 24px;box-shadow:0 1px 3px rgba(0,0,0,0.06);height:100%;">'

        f'<div style="font-size:10px;font-weight:700;color:#5B6472;text-transform:uppercase;'
        f'letter-spacing:0.08em;margin-bottom:6px;">Total Portfolio Value</div>'

        f'<div style="font-size:34px;font-weight:800;color:#0B0B0F;letter-spacing:-0.04em;'
        f'line-height:1.1;margin-bottom:4px;">{fmt_currency(p["total_value"])}</div>'

        f'<div style="font-size:15px;font-weight:600;color:{daily_color};margin-bottom:22px;">'
        f'{daily_icon} {fmt_currency(abs(p["daily_change_dollars"]))} '
        f'({fmt_pct(abs(p["daily_change_pct"]))}) today</div>'

        f'<div style="height:1px;background:#E2E8F0;margin-bottom:18px;"></div>'

        f'<div style="display:flex;flex-direction:column;gap:11px;">'

        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-size:12px;color:#5B6472;">Cash</span>'
        f'<span style="font-size:13px;font-weight:600;color:#0B0B0F;">'
        f'{fmt_currency(p["cash"])} ({fmt_pct(p["cash_pct"])})</span></div>'

        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-size:12px;color:#5B6472;">Invested</span>'
        f'<span style="font-size:13px;font-weight:600;color:#0B0B0F;">{fmt_currency(p["invested"])}</span></div>'

        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-size:12px;color:#5B6472;">Beta</span>'
        f'<span style="font-size:13px;font-weight:600;color:#0B0B0F;">{p["portfolio_beta"]:.2f}</span></div>'

        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-size:12px;color:#5B6472;">Holdings</span>'
        f'<span style="font-size:13px;font-weight:600;color:#0B0B0F;">{p["num_holdings"]} positions</span></div>'

        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-size:12px;color:#5B6472;">Rebalance</span>'
        f'<span style="font-size:13px;font-weight:600;color:{rebal_color};">{rebal_text}</span></div>'

        f'</div></div>'
    )


def _sector_chart(sector_exposure: dict):
    render_section_header("Sector Allocation", "Portfolio distribution by sector · hover for details", "🗂️")

    if not sector_exposure or not _PLOTLY:
        # Fallback: simple bar chart if plotly unavailable
        import altair as alt
        data = pd.DataFrame(
            [{"Sector": s, "Weight (%)": w} for s, w in sector_exposure.items()]
        ).sort_values("Weight (%)", ascending=True)
        data["colour"] = data["Weight (%)"].apply(lambda w: "#DC2626" if w >= 25 else "#061A33")
        chart = (
            alt.Chart(data)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("Weight (%):Q"),
                y=alt.Y("Sector:N", sort=None, title=""),
                color=alt.Color("colour:N", scale=None),
                tooltip=["Sector", alt.Tooltip("Weight (%):Q", format=".1f")],
            )
            .properties(height=280)
        )
        st.altair_chart(chart, use_container_width=True)
        return

    labels = list(sector_exposure.keys())
    values = list(sector_exposure.values())
    colors = [_SECTOR_COLORS.get(s, "#94a3b8") for s in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.58,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        sort=True,
        direction="clockwise",
    )])

    fig.add_annotation(
        text=f"<b>{len([v for v in values if v > 0])}</b><br>Sectors",
        x=0.5, y=0.5,
        font=dict(size=15, color="#0B0B0F", family="Inter, sans-serif"),
        showarrow=False,
        align="center",
    )

    fig.update_layout(
        showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=0, r=0),
        height=340,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=11, color="#5B6472", family="Inter, sans-serif"),
            bgcolor="rgba(0,0,0,0)",
            itemclick=False,
            itemdoubleclick=False,
        ),
        font=dict(family="Inter, sans-serif"),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _rebalance_table(holdings: list):
    render_section_header(
        "Holdings",
        "Live prices · click any column header to sort",
        "📋",
    )

    rows = []
    for h in holdings:
        pnl_pct = (h["current_price"] - h["avg_cost"]) / h["avg_cost"] if h.get("avg_cost") else 0
        rows.append({
            "Ticker":   h["ticker"],
            "Company":  h["name"],
            "Sector":   h["sector"],
            "Price":    fmt_currency(h["current_price"]),
            "Today %":  fmt_pct(h.get("change_pct", 0)),
            "Value":    fmt_currency(h["market_value"]),
            "P&L %":    fmt_pct(pnl_pct),
            "Weight":   fmt_weight(h["current_weight"]),
            "Action":   _ACTION_DISPLAY.get(h.get("action", "Hold"), h.get("action", "Hold")),
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        height=min(520, 45 + len(rows) * 37),
    )


def _trade_summary(holdings: list):
    sells = [h for h in holdings if h.get("trade_dir") == "Sell"]
    buys  = [h for h in holdings if h.get("trade_dir") == "Buy"]

    if not sells and not buys:
        st.success("✅ Portfolio is on target — no trades required.")
        return

    render_section_header("Trade Plan", "Execute to bring portfolio back to target weights", "🔄")

    col_sell, col_buy = st.columns(2, gap="medium")

    with col_sell:
        if sells:
            total      = sum(h["trade_value"] for h in sells)
            items_html = "".join(
                f'<div style="font-size:13px;color:#374151;padding:3px 0;">'
                f'· <strong>{h["ticker"]}</strong> — Sell {fmt_currency(h["trade_value"])}</div>'
                for h in sells
            )
            render_html(
                f'<div style="background:#fef2f2;border:1px solid #fecaca;'
                f'border-radius:12px;padding:16px 20px;">'
                f'<div style="font-size:12px;font-weight:700;color:#991b1b;margin-bottom:10px;">'
                f'🔴 Trim / Sell — {fmt_currency(total)} total</div>'
                f'{items_html}</div>'
            )

    with col_buy:
        if buys:
            total      = sum(h["trade_value"] for h in buys)
            items_html = "".join(
                f'<div style="font-size:13px;color:#374151;padding:3px 0;">'
                f'· <strong>{h["ticker"]}</strong> — Buy {fmt_currency(h["trade_value"])}</div>'
                for h in buys
            )
            render_html(
                f'<div style="background:#f0fdf4;border:1px solid #86efac;'
                f'border-radius:12px;padding:16px 20px;">'
                f'<div style="font-size:12px;font-weight:700;color:#166534;margin-bottom:10px;">'
                f'🟢 Add / Buy — {fmt_currency(total)} total</div>'
                f'{items_html}</div>'
            )


def _concentration_panel(holdings: list):
    render_section_header("Concentration", "Top positions by weight", "🔍")

    sorted_h  = sorted(holdings, key=lambda h: h["current_weight"], reverse=True)
    top3      = sum(h["current_weight"] for h in sorted_h[:3])
    top3_ok   = top3 <= 30.0

    rows = [
        {
            "Ticker": h["ticker"],
            "Weight": fmt_weight(h["current_weight"]),
            "Target": fmt_weight(h["target_weight"]),
        }
        for h in sorted_h[:5]
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    colour = "#16A34A" if top3_ok else "#DC2626"
    note   = "Within 30% limit" if top3_ok else "Exceeds 30% — review"
    render_html(
        f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;'
        f'padding:14px 16px;margin-top:10px;">'
        f'<div style="font-size:10px;color:#5B6472;text-transform:uppercase;'
        f'letter-spacing:0.07em;font-weight:600;margin-bottom:4px;">Top 3 Combined</div>'
        f'<div style="font-size:22px;font-weight:700;color:#0B0B0F;">{fmt_weight(top3)}</div>'
        f'<div style="font-size:12px;font-weight:600;color:{colour};margin-top:2px;">{note}</div>'
        f'</div>'
    )


def _risk_warnings():
    if not RISK_ALERTS:
        return
    render_section_header("Risk Warnings", f"{len(RISK_ALERTS)} active alerts", "⚠️")
    level_map  = {"warning": "warning", "danger": "critical", "info": "info"}
    action_map = {"danger": "Immediate action required", "warning": "Monitor closely", "info": "For your awareness"}
    for alert in RISK_ALERTS:
        raw = alert["level"]
        render_risk_alert(
            message=alert["message"],
            level=level_map.get(raw, "warning"),
            recommended_action=action_map.get(raw, ""),
        )
