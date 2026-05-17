"""
dashboard.py — Premium fintech dashboard redesign.

All backend logic (_build_live_summary, _build_live_opportunities) is unchanged.
Only the UI rendering functions are replaced.
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

from components import render_metric_card, render_html
from utils.sample_data import (
    PORTFOLIO_HOLDINGS,
    PORTFOLIO_SUMMARY,
    DAILY_DECISIONS,
    RISK_ALERTS,
    OPPORTUNITIES,
    NEWS_ITEMS,
    WATCHLIST,
    RESEARCH_WATCHLIST,
)
from utils.formatting import fmt_currency, fmt_pct
from services import market_data_service, macro_service


# ── Sector colors (mirrored from watchlist) ───────────────────────────────────

_SECTOR_BG = {
    "Technology":               "#2563EB",
    "Consumer Staples":         "#16A34A",
    "Consumer Discretionary":   "#059669",
    "Financials":               "#0284C7",
    "Healthcare":               "#7C3AED",
    "Industrials":              "#D97706",
    "Communication Services":   "#0EA5E9",
    "Energy":                   "#EA580C",
    "Materials":                "#65A30D",
    "Real Estate":              "#DC2626",
    "Utilities":                "#6366F1",
}

_REGIME_CSS = {
    "risk-on":  "db-regime-risk-on",
    "Neutral":  "db-regime-neutral",
    "risk-off": "db-regime-risk-off",
    "crisis":   "db-regime-crisis",
}
_REGIME_ICON = {"risk-on": "🟢", "Neutral": "🟡", "risk-off": "🟠", "crisis": "🔴"}


# ── Backend data builders (UNCHANGED) ─────────────────────────────────────────

def _build_live_summary() -> tuple[dict, bool]:
    tickers     = [h["ticker"] for h in PORTFOLIO_HOLDINGS]
    live_prices = market_data_service.get_portfolio_prices(tickers)
    prices_live = False
    daily_pnl   = 0.0
    total_invested = 0.0

    for h in PORTFOLIO_HOLDINGS:
        price_data = live_prices.get(h["ticker"])
        if price_data and price_data.get("price"):
            live_price   = price_data["price"]
            market_value = live_price * h["shares"]
            change_pct   = price_data.get("change_pct", 0) or 0
            daily_pnl   += market_value * change_pct
            prices_live  = True
        else:
            market_value = h["market_value"]
        total_invested += market_value

    cash        = PORTFOLIO_SUMMARY["cash"]
    total_value = total_invested + cash

    summary = PORTFOLIO_SUMMARY.copy()
    summary["total_value"]          = round(total_value, 2)
    summary["invested"]             = round(total_invested, 2)
    summary["cash_pct"]             = round(cash / total_value, 4) if total_value else 0
    summary["num_holdings"]         = len(PORTFOLIO_HOLDINGS)
    summary["daily_change_dollars"] = round(daily_pnl, 2)
    summary["daily_change_pct"]     = round(daily_pnl / (total_value - daily_pnl), 4) if total_value else 0

    return summary, prices_live, live_prices


def _build_live_opportunities() -> list:
    tickers     = [o["ticker"] for o in OPPORTUNITIES]
    live_prices = market_data_service.get_watchlist_prices(tickers)
    enriched = []
    for opp in OPPORTUNITIES:
        item       = opp.copy()
        price_data = live_prices.get(opp["ticker"])
        if price_data and price_data.get("price"):
            live_price    = price_data["price"]
            item["price"] = live_price
            if item.get("buy_below"):
                item["upside_pct"] = (item["buy_below"] - live_price) / live_price
        enriched.append(item)
    return enriched


# ── HTML fragment helpers ─────────────────────────────────────────────────────

def _chg_pill(pct: float, has_data: bool = True) -> str:
    if not has_data:
        return '<span class="db-chg-neu">—</span>'
    if pct > 0.0001:
        return f'<span class="db-chg-pos">▲ +{pct:.2f}%</span>'
    if pct < -0.0001:
        return f'<span class="db-chg-neg">▼ {pct:.2f}%</span>'
    return '<span class="db-chg-neu">—</span>'


def _act_badge(action: str) -> str:
    palette = {
        "buy":   ("#DCFCE7", "#15803D"),
        "add":   ("#DBEAFE", "#1D4ED8"),
        "hold":  ("#F1F5F9", "#475569"),
        "watch": ("#FEF3C7", "#D97706"),
        "trim":  ("#FED7AA", "#C2410C"),
        "sell":  ("#FEE2E2", "#DC2626"),
    }
    bg, fg = palette.get(action.lower(), ("#F1F5F9", "#475569"))
    return (
        f'<span style="background:{bg};color:{fg};font-size:11px;font-weight:700;'
        f'padding:2px 9px;border-radius:999px;white-space:nowrap;">{action}</span>'
    )


def _sent_badge(sentiment: str) -> str:
    palette = {
        "Positive": ("#DCFCE7", "#15803D"),
        "Negative": ("#FEE2E2", "#DC2626"),
        "Mixed":    ("#FEF3C7", "#D97706"),
        "Neutral":  ("#F1F5F9", "#64748B"),
    }
    bg, fg = palette.get(sentiment, ("#F1F5F9", "#64748B"))
    return (
        f'<span style="background:{bg};color:{fg};font-size:10px;font-weight:700;'
        f'padding:2px 8px;border-radius:999px;">{sentiment}</span>'
    )


def _score_pill(score: int) -> str:
    if score >= 80:
        bg, fg = "#DCFCE7", "#15803D"
    elif score >= 65:
        bg, fg = "#DBEAFE", "#1D4ED8"
    elif score >= 50:
        bg, fg = "#F1F5F9", "#475569"
    else:
        bg, fg = "#FEE2E2", "#DC2626"
    return (
        f'<span style="background:{bg};color:{fg};font-size:11px;font-weight:700;'
        f'padding:2px 8px;border-radius:999px;">{score}</span>'
    )


def _card(title: str, subtitle: str = "") -> str:
    sub = f'<span class="db-card-sub">· {subtitle}</span>' if subtitle else ""
    return f'<div class="db-card"><div class="db-card-title">{title}{sub}</div>'


def _empty(icon: str, title: str, sub: str) -> None:
    st.markdown(
        f'<div class="db-empty-state">'
        f'<div class="db-empty-icon">{icon}</div>'
        f'<div class="db-empty-title">{title}</div>'
        f'<div class="db-empty-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    summary, prices_live, portfolio_prices = _build_live_summary()
    regime      = macro_service.get_market_regime()
    opportunities = _build_live_opportunities()
    indices     = market_data_service.get_market_indices()

    # Fetch watchlist live prices for movers section
    wl_tickers  = [s["ticker"] for s in WATCHLIST] + [r["ticker"] for r in RESEARCH_WATCHLIST]
    wl_prices   = market_data_service.get_watchlist_prices(wl_tickers) if wl_tickers else {}

    _page_header(prices_live)
    _metric_cards(summary)
    _regime_banner(regime)

    c_left, c_mid, c_right = st.columns(3, gap="medium")
    with c_left:
        _decisions_card()
    with c_mid:
        _opportunities_card(opportunities)
    with c_right:
        _alerts_card()

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

    c_a, c_b, c_c = st.columns(3, gap="medium")
    with c_a:
        _sector_chart(PORTFOLIO_HOLDINGS, portfolio_prices)
    with c_b:
        _top_holdings(PORTFOLIO_HOLDINGS, portfolio_prices)
    with c_c:
        _market_overview(indices)

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

    c_x, c_y, c_z = st.columns(3, gap="medium")
    with c_x:
        _intel_feed()
    with c_y:
        _upcoming_events()
    with c_z:
        _watchlist_movers(wl_prices)


# ── Page header ───────────────────────────────────────────────────────────────

def _page_header(prices_live: bool):
    today      = datetime.now().strftime("%A, %d %B %Y")
    data_color = "#16A34A" if prices_live else "#D97706"
    data_label = "Live Data" if prices_live else "Prices Unavailable"

    col_title, col_btn = st.columns([6, 1], gap="small")
    with col_title:
        render_html(
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">'
            f'<span class="db-page-title">Dashboard</span>'
            f'<span style="background:{data_color}22;color:{data_color};font-size:11px;'
            f'font-weight:700;padding:3px 10px;border-radius:999px;'
            f'border:1px solid {data_color}44;">● {data_label}</span>'
            f'</div>'
            f'<div class="db-page-sub">{today}</div>'
        )
    with col_btn:
        st.markdown('<div style="padding-top:8px;"></div>', unsafe_allow_html=True)
        if st.button("↻ Refresh", use_container_width=True):
            st.rerun()

    st.markdown(
        '<div style="height:1px;background:#E2E8F0;margin:14px 0 22px;"></div>',
        unsafe_allow_html=True,
    )


# ── Metric cards ─────────────────────────────────────────────────────────────

def _metric_cards(p: dict):
    daily_up  = p["daily_change_pct"] >= 0
    weekly_up = p.get("weekly_change_pct", 0) >= 0
    health    = p["health_score"]

    health_label = "Strong" if health >= 70 else ("Fair" if health >= 50 else "Weak")
    health_icon  = "✅" if health >= 70 else ("⚠️" if health >= 50 else "❌")
    health_type  = "positive" if health >= 70 else ("neutral" if health >= 50 else "negative")

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        render_metric_card(
            label="Total Value", value=fmt_currency(p["total_value"]),
            delta=fmt_pct(p["daily_change_pct"]) + " today",
            delta_type="positive" if daily_up else "negative",
            icon="💼", accent=True,
        )
    with c2:
        render_metric_card(
            label="Daily P&L", value=fmt_currency(abs(p["daily_change_dollars"])),
            delta=fmt_pct(p["daily_change_pct"]),
            delta_type="positive" if daily_up else "negative",
            icon="📈" if daily_up else "📉",
        )
    with c3:
        render_metric_card(
            label="Cash Balance", value=fmt_currency(p["cash"]),
            delta=fmt_pct(p["cash_pct"]) + " of portfolio",
            delta_type="neutral", icon="💵",
        )

    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3, gap="medium")
    with c4:
        render_metric_card(
            label="Invested", value=fmt_currency(p["invested"]),
            delta=f"{p['num_holdings']} positions",
            delta_type="neutral", icon="📊",
        )
    with c5:
        render_metric_card(
            label="Weekly P&L", value=fmt_currency(abs(p.get("weekly_change_dollars", 0))),
            delta=fmt_pct(p.get("weekly_change_pct", 0)),
            delta_type="positive" if weekly_up else "negative",
            icon="📅",
        )
    with c6:
        render_metric_card(
            label="Health Score", value=f"{health}/100",
            delta=f"{health_icon} {health_label}",
            delta_type=health_type, icon="❤️", accent=True,
        )

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)


# ── Regime banner ─────────────────────────────────────────────────────────────

def _regime_banner(r: dict | None):
    if not r:
        st.warning("Market regime unavailable — VIX data could not be fetched.")
        return

    css_cls = _REGIME_CSS.get(r["regime"], "db-regime-neutral")
    icon    = _REGIME_ICON.get(r["regime"], "⚪")

    buying_rule = r["buying_rule"]
    for emoji in ("🟢 ", "🟡 ", "🔴 ", "🚨 "):
        buying_rule = buying_rule.replace(emoji, "")

    summary_short = r["summary"].split(".")[0] + "."

    vix_str  = f"VIX {r['vix']:.1f}"
    sp_str   = f"S&P {r['sp500_trend']}"

    st.markdown(
        f'<div class="db-regime {css_cls}">'
        f'<div class="db-regime-icon">{icon}</div>'
        f'<div class="db-regime-body">'
        f'<div class="db-regime-label">Market Regime</div>'
        f'<div class="db-regime-title">{r["regime"]} — {buying_rule}</div>'
        f'<div class="db-regime-meta">{vix_str} &nbsp;·&nbsp; {sp_str} &nbsp;·&nbsp; {summary_short}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)


# ── Today's Decisions ─────────────────────────────────────────────────────────

def _decisions_card():
    actionable = sum(1 for d in DAILY_DECISIONS if d.get("action") in ("Buy", "Add"))
    sub = f"{actionable} actionable" if DAILY_DECISIONS else "no active signals"

    st.markdown(_card("📋 Today's Decisions", sub), unsafe_allow_html=True)

    if not DAILY_DECISIONS:
        _empty("📋", "No active decisions today",
               "Decision signals will appear here when your watchlist analysis is updated.")
    else:
        rows = ""
        for d in DAILY_DECISIONS[:6]:
            rows += (
                f'<div class="db-decision-row">'
                f'<div style="flex:0 0 auto;">'
                f'<div class="db-d-ticker">{d["ticker"]}</div>'
                f'<div class="db-d-name">{d["name"]}</div>'
                f'</div>'
                f'<div class="db-d-reason">{d["reason"]}</div>'
                f'{_act_badge(d.get("action","Hold"))}'
                f'</div>'
            )
        st.markdown(rows + '</div>', unsafe_allow_html=True)
        return

    st.markdown('</div>', unsafe_allow_html=True)


# ── Best Opportunities ────────────────────────────────────────────────────────

def _opportunities_card(opps: list):
    sub = f"{len(opps)} near buy range" if opps else "none currently"
    st.markdown(_card("🎯 Best Opportunities", sub), unsafe_allow_html=True)

    if not opps:
        _empty("🎯", "No current opportunities",
               "Opportunities appear when watchlist stocks approach their buy-below targets.")
    else:
        rows = ""
        for opp in opps[:5]:
            upside = opp.get("upside_pct", 0)
            up_col = "#16A34A" if upside >= 0 else "#DC2626"
            sign   = "+" if upside >= 0 else ""
            rows += (
                f'<div class="db-row" style="gap:10px;">'
                f'<div style="flex:1;min-width:0;">'
                f'<div style="font-size:13px;font-weight:700;color:#0F172A;">{opp["ticker"]}</div>'
                f'<div style="font-size:11px;color:#64748B;">{opp["name"]}</div>'
                f'</div>'
                f'<div style="text-align:right;">'
                f'<div style="font-size:13px;font-weight:700;color:{up_col};">{sign}{upside*100:.1f}%</div>'
                f'<div style="margin-top:2px;">{_act_badge(opp.get("action","Watch"))}</div>'
                f'</div>'
                f'</div>'
            )
        st.markdown(rows + '</div>', unsafe_allow_html=True)
        return

    st.markdown('</div>', unsafe_allow_html=True)


# ── Risk Alerts ───────────────────────────────────────────────────────────────

def _alerts_card():
    critical = sum(1 for a in RISK_ALERTS if a.get("level") == "danger")
    sub = f"{critical} critical" if critical else ("none active" if not RISK_ALERTS else f"{len(RISK_ALERTS)} active")

    st.markdown(_card("⚠️ Risk Alerts", sub), unsafe_allow_html=True)

    if not RISK_ALERTS:
        _empty("✅", "No active risk alerts",
               "Risk alerts are generated dynamically from your live portfolio data in Risk Centre.")
    else:
        level_cfg = {
            "danger":  ("#FEF2F2", "#991B1B", "🚨"),
            "warning": ("#FFFBEB", "#92400E", "⚠️"),
            "info":    ("#EFF6FF", "#1E40AF", "ℹ️"),
        }
        rows = ""
        for a in RISK_ALERTS[:5]:
            bg, fg, ico = level_cfg.get(a.get("level", "warning"), ("#FFFBEB", "#92400E", "⚠️"))
            rows += (
                f'<div style="background:{bg};border-radius:10px;padding:10px 12px;'
                f'margin-bottom:6px;display:flex;gap:8px;align-items:flex-start;">'
                f'<span style="font-size:14px;flex-shrink:0;">{ico}</span>'
                f'<span style="font-size:12px;color:{fg};line-height:1.45;">{a["message"]}</span>'
                f'</div>'
            )
        st.markdown(rows + '</div>', unsafe_allow_html=True)
        return

    st.markdown('</div>', unsafe_allow_html=True)


# ── Sector Allocation Donut ───────────────────────────────────────────────────

def _sector_chart(holdings: list, live_prices: dict):
    st.markdown(_card("🗂️ Sector Allocation"), unsafe_allow_html=True)

    sector_vals: dict[str, float] = {}
    for h in holdings:
        price = live_prices.get(h["ticker"], {}).get("price") or h.get("current_price", 0)
        val   = (price or 0) * h["shares"]
        sector_vals[h["sector"]] = sector_vals.get(h["sector"], 0) + val

    if not sector_vals:
        _empty("🗂️", "No holdings data", "Portfolio sector data unavailable.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    total  = sum(sector_vals.values())
    labels = list(sector_vals.keys())
    values = [v / total * 100 for v in sector_vals.values()]
    colors = [_SECTOR_BG.get(s, "#64748B") for s in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{len(holdings)}</b><br>Holdings",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=13, color="#0F172A", family="Inter, sans-serif"),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=0, b=0, l=0, r=120),
        showlegend=True,
        legend=dict(
            orientation="v", x=1.02, y=0.5,
            font=dict(size=11, color="#475569", family="Inter, sans-serif"),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=230,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)


# ── Top Holdings ──────────────────────────────────────────────────────────────

def _top_holdings(holdings: list, live_prices: dict):
    st.markdown(_card("💼 Top Holdings", "by portfolio weight"), unsafe_allow_html=True)

    sorted_h = sorted(holdings, key=lambda x: x.get("current_weight", 0), reverse=True)
    rows = ""
    for h in sorted_h[:7]:
        price = live_prices.get(h["ticker"], {}).get("price") or h.get("current_price", 0)
        cost  = h.get("avg_cost", price)
        pnl   = (price - cost) / cost if cost else 0
        bg    = _SECTOR_BG.get(h["sector"], "#0B1628")
        pnl_cls = "db-h-pnl-pos" if pnl >= 0 else "db-h-pnl-neg"
        sign    = "+" if pnl >= 0 else ""
        rows += (
            f'<div class="db-holding-row">'
            f'<div class="db-h-circle" style="background:{bg};">{h["ticker"][:2]}</div>'
            f'<div style="margin-left:10px;flex:1;min-width:0;">'
            f'<div class="db-h-ticker">{h["ticker"]}</div>'
            f'<div class="db-h-sector">{h["sector"]}</div></div>'
            f'<div style="text-align:right;">'
            f'<div class="db-h-weight">{h.get("current_weight",0):.1f}%</div>'
            f'<div class="{pnl_cls}">{sign}{pnl*100:.1f}%</div></div>'
            f'</div>'
        )
    st.markdown(rows + '</div>', unsafe_allow_html=True)


# ── Market Overview ───────────────────────────────────────────────────────────

def _market_overview(indices: list | None):
    st.markdown(_card("🌍 Market Overview", "today's snapshot"), unsafe_allow_html=True)

    if not indices:
        _empty("🌍", "Market data unavailable", "Index data could not be fetched from providers.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    rows = ""
    for idx in indices:
        chg     = idx.get("change_pct", 0) or 0
        is_vix  = idx["name"] == "VIX"
        good    = (chg < 0) if is_vix else (chg >= 0)
        pill    = f'<span class="{"db-chg-pos" if good else "db-chg-neg"}">'
        sign    = "+" if chg >= 0 else ""
        rows += (
            f'<div class="db-mkt-row">'
            f'<div class="db-mkt-name">{idx["name"]}</div>'
            f'<div class="db-mkt-val">{idx["value"]:,.2f}</div>'
            f'{pill}{sign}{chg:.2f}%</span>'
            f'</div>'
        )
    st.markdown(rows + '</div>', unsafe_allow_html=True)


# ── Intelligence Feed ─────────────────────────────────────────────────────────

def _intel_feed():
    positive = sum(1 for n in NEWS_ITEMS if n.get("sentiment") == "Positive")
    st.markdown(_card("🧠 Intelligence Feed", f"{len(NEWS_ITEMS)} analyses · {positive} bullish"), unsafe_allow_html=True)

    if not NEWS_ITEMS:
        _empty("🧠", "No intelligence items", "AI analyst items will appear here.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    rows = ""
    for item in NEWS_ITEMS[:4]:
        rows += (
            f'<div class="db-intel-item">'
            f'<div class="db-intel-header">'
            f'<span style="font-size:12px;font-weight:700;color:#0F172A;">{item["ticker"]}</span>'
            f'{_sent_badge(item.get("sentiment","Neutral"))}'
            f'<span style="font-size:11px;color:#94A3B8;margin-left:auto;">'
            f'{item.get("thesis","—")}</span>'
            f'</div>'
            f'<div class="db-intel-summary">{item.get("summary","")[:120]}…</div>'
            f'</div>'
        )
    st.markdown(rows + '</div>', unsafe_allow_html=True)


# ── Upcoming Events (placeholder) ────────────────────────────────────────────

def _upcoming_events():
    st.markdown(_card("📅 Upcoming Events"), unsafe_allow_html=True)
    _empty("📅", "No upcoming events found",
           "Earnings dates, macro events, and dividend dates will appear here when data is available.")
    st.markdown('</div>', unsafe_allow_html=True)


# ── Watchlist Movers ─────────────────────────────────────────────────────────

def _watchlist_movers(wl_prices: dict):
    movers = [
        (ticker, data["price"], data["change_pct"])
        for ticker, data in wl_prices.items()
        if data.get("price") and data.get("change_pct") is not None
    ]
    movers.sort(key=lambda x: abs(x[2]), reverse=True)

    st.markdown(_card("⚡ Watchlist Movers", f"{len(movers)} with live data"), unsafe_allow_html=True)

    if not movers:
        _empty("⚡", "No mover data available", "Live watchlist prices could not be fetched.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    gainers = [m for m in movers if m[2] >= 0][:3]
    losers  = [m for m in movers if m[2] < 0][:3]

    rows = ""
    if gainers:
        rows += '<div style="font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;padding:4px 0 6px;">Top Gainers</div>'
        for ticker, price, chg in gainers:
            rows += (
                f'<div class="db-mkt-row">'
                f'<div class="db-mkt-name">{ticker}</div>'
                f'<div class="db-mkt-val">{fmt_currency(price)}</div>'
                f'<span class="db-chg-pos">+{chg:.2f}%</span>'
                f'</div>'
            )
    if losers:
        rows += '<div style="font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;padding:10px 0 6px;">Top Losers</div>'
        for ticker, price, chg in losers:
            rows += (
                f'<div class="db-mkt-row">'
                f'<div class="db-mkt-name">{ticker}</div>'
                f'<div class="db-mkt-val">{fmt_currency(price)}</div>'
                f'<span class="db-chg-neg">{chg:.2f}%</span>'
                f'</div>'
            )

    st.markdown(rows + '</div>', unsafe_allow_html=True)
