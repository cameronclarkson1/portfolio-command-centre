"""
watchlist.py — Watchlist page. Premium fintech redesign.

All data sources, live-price fetching, and calculations are unchanged.
Only the UI rendering functions are replaced.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from components import render_section_header, render_metric_card, render_html, now_str
from utils.sample_data import PORTFOLIO_HOLDINGS, PORTFOLIO_SUMMARY, WATCHLIST, RESEARCH_WATCHLIST
from utils.formatting import fmt_currency, fmt_pct
from services import market_data_service


# ── Sector → ticker circle color ─────────────────────────────────────────────

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


# ── HTML fragment builders ────────────────────────────────────────────────────

def _circle(ticker: str, sector: str = "") -> str:
    bg = _SECTOR_BG.get(sector, "#0B1628")
    return f'<div class="wl-circle" style="background:{bg};">{ticker[:2].upper()}</div>'


def _score_pill(score: int) -> str:
    if score >= 80:
        return f'<span class="wl-pill wl-pill-green">{score}</span>'
    if score >= 65:
        return f'<span class="wl-pill wl-pill-blue">{score}</span>'
    if score >= 50:
        return f'<span class="wl-pill wl-pill-grey">{score}</span>'
    if score > 0:
        return f'<span class="wl-pill wl-pill-red">{score}</span>'
    return '<span class="wl-pill wl-pill-muted">—</span>'


def _change_pill(change: float, has_data: bool = True) -> str:
    if not has_data:
        return '<span class="wl-chg wl-chg-neu">—</span>'
    if change > 0.0001:
        return f'<span class="wl-chg wl-chg-pos">▲ +{change:.2f}%</span>'
    if change < -0.0001:
        return f'<span class="wl-chg wl-chg-neg">▼ {change:.2f}%</span>'
    return '<span class="wl-chg wl-chg-neu">0.00%</span>'


def _pnl_pill(pct: float) -> str:
    if pct > 0.0001:
        return f'<span class="wl-chg wl-chg-pos">▲ +{pct*100:.1f}%</span>'
    if pct < -0.0001:
        return f'<span class="wl-chg wl-chg-neg">▼ {pct*100:.1f}%</span>'
    return '<span class="wl-chg wl-chg-neu">0.0%</span>'


def _act_badge(action: str) -> str:
    key = action.lower()
    valid = {"buy", "add", "hold", "watch", "trim", "sell", "avoid"}
    css = f"wl-act wl-act-{key}" if key in valid else "wl-act wl-act-hold"
    return f'<span class="{css}">{action}</span>'


def _status_badge(status: str) -> str:
    m = {
        "portfolio": "wl-status wl-status-portfolio",
        "watchlist":  "wl-status wl-status-watchlist",
        "research":   "wl-status wl-status-research",
    }
    css = m.get(status.lower(), "wl-status wl-status-watchlist")
    return f'<span class="{css}">{status.title()}</span>'


def _upside_html(pct) -> str:
    if pct is None:
        return '<span style="color:#94A3B8;font-size:13px;">—</span>'
    col  = "#16A34A" if pct >= 0 else "#DC2626"
    sign = "+" if pct >= 0 else ""
    return f'<span style="color:{col};font-weight:600;font-size:13px;">{sign}{pct*100:.1f}%</span>'


def _wl_table(header_cols: list[tuple], rows: list[str], caption: str = "") -> None:
    """Render a complete custom HTML table card in one st.markdown call."""
    header_html = "".join(
        f'<div class="{cls}">{label}</div>' for label, cls in header_cols
    )
    rows_html = "".join(rows)
    cap_html  = f'<div class="wl-caption">{caption}</div>' if caption else ""
    st.markdown(
        f'<div class="wl-card">'
        f'<div class="wl-thead">{header_html}</div>'
        f'{rows_html}'
        f'</div>{cap_html}',
        unsafe_allow_html=True,
    )


# ── Main entry point ──────────────────────────────────────────────────────────

def render():
    # One batch price call — all tickers across all three lists (unchanged)
    all_tickers = (
        [h["ticker"] for h in PORTFOLIO_HOLDINGS]
        + [s["ticker"] for s in WATCHLIST]
        + [r["ticker"] for r in RESEARCH_WATCHLIST]
    )
    live_prices = market_data_service.get_watchlist_prices(all_tickers)

    prices_live = any(v.get("price") for v in live_prices.values())
    if not prices_live:
        st.warning("Live prices unavailable — showing snapshot values. Check API connection.")

    _header(live_prices)
    _summary_cards()

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    total = len(PORTFOLIO_HOLDINGS) + len(WATCHLIST) + len(RESEARCH_WATCHLIST)
    tab_all, tab1, tab2, tab3 = st.tabs([
        f"All  ({total})",
        f"Portfolio  ({len(PORTFOLIO_HOLDINGS)})",
        f"Watchlist  ({len(WATCHLIST)})",
        f"Research Pipeline  ({len(RESEARCH_WATCHLIST)})",
    ])

    with tab_all:
        _all_tab(live_prices)
    with tab1:
        _portfolio_tab(live_prices)
    with tab2:
        _watchlist_tab(live_prices)
    with tab3:
        _research_tab(live_prices)

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    _insight_cards(live_prices)


# ── Header ────────────────────────────────────────────────────────────────────

def _header(live_prices: dict):
    total = len(PORTFOLIO_HOLDINGS) + len(WATCHLIST) + len(RESEARCH_WATCHLIST)
    col_title, col_search, col_btn = st.columns([3, 2, 1], gap="small")

    with col_title:
        render_html(
            f'<div class="wl-page-title">Watchlist</div>'
            f'<div class="wl-page-subtitle">'
            f'{total} symbols &nbsp;·&nbsp; {len(PORTFOLIO_HOLDINGS)} held &nbsp;·&nbsp; '
            f'{len(WATCHLIST)} monitored &nbsp;·&nbsp; {len(RESEARCH_WATCHLIST)} in research pipeline'
            f'&nbsp;·&nbsp; Updated {now_str()}</div>'
        )

    with col_search:
        st.markdown('<div style="padding-top:6px;"></div>', unsafe_allow_html=True)
        st.text_input(
            "search",
            placeholder="Search ticker or company…",
            label_visibility="collapsed",
            key="wl_global_search",
        )

    with col_btn:
        st.markdown('<div style="padding-top:6px;"></div>', unsafe_allow_html=True)
        if st.button("+ Add Ticker", use_container_width=True, type="primary"):
            st.info("Ticker management — add via Stock Research page.", icon="ℹ️")

    st.markdown(
        '<div style="height:1px;background:#E2E8F0;margin:16px 0 20px;"></div>',
        unsafe_allow_html=True,
    )


# ── Summary cards ─────────────────────────────────────────────────────────────

def _summary_cards():
    researched = sum(1 for s in WATCHLIST if s.get("final_score", 0) > 0)
    high_score = sum(
        1 for s in WATCHLIST
        if s.get("final_score", 0) >= 70
    ) + sum(
        1 for h in PORTFOLIO_HOLDINGS
        if h.get("final_score", 0) >= 70
    )
    total = len(PORTFOLIO_HOLDINGS) + len(WATCHLIST) + len(RESEARCH_WATCHLIST)

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        render_metric_card(
            label="Total Tracked", value=str(total),
            delta="across all lists", delta_type="neutral", icon="📋", accent=True,
        )
    with c2:
        render_metric_card(
            label="Portfolio Holdings", value=str(len(PORTFOLIO_HOLDINGS)),
            delta="active positions", delta_type="neutral", icon="💼",
        )
    with c3:
        render_metric_card(
            label="Watchlist", value=str(len(WATCHLIST)),
            delta=f"{researched} fully researched", delta_type="neutral", icon="👁️",
        )
    with c4:
        render_metric_card(
            label="Research Pipeline", value=str(len(RESEARCH_WATCHLIST)),
            delta="potential buys", delta_type="neutral", icon="🔭",
        )


# ── Tab: All ──────────────────────────────────────────────────────────────────

def _all_tab(live_prices: dict):
    render_section_header(
        "All Tracked Symbols",
        "Portfolio holdings, watchlist, and research pipeline combined",
        "📊",
    )

    col_filter, col_sector, _ = st.columns([2, 2, 4], gap="small")
    with col_filter:
        sector_filter = st.selectbox(
            "Sector", ["All Sectors"] + sorted({h["sector"] for h in PORTFOLIO_HOLDINGS}
                | {s["sector"] for s in WATCHLIST}
                | {r["sector"] for r in RESEARCH_WATCHLIST}),
            label_visibility="collapsed", key="all_sector",
        )
    with col_sector:
        status_filter = st.selectbox(
            "Status", ["All", "Portfolio", "Watchlist", "Research"],
            label_visibility="collapsed", key="all_status",
        )

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    header_cols = [
        ("Ticker",  "wl-c-ticker"),
        ("Price",   "wl-c-price"),
        ("Today",   "wl-c-change"),
        ("AI Score","wl-c-score"),
        ("Sector",  "wl-c-sector"),
        ("Action",  "wl-c-action"),
        ("Status",  "wl-c-status"),
    ]

    rows = []

    def _maybe(ticker, field, live_prices):
        pd_data = live_prices.get(ticker, {})
        return pd_data.get(field)

    # Portfolio holdings
    if status_filter in ("All", "Portfolio"):
        for h in PORTFOLIO_HOLDINGS:
            if sector_filter not in ("All Sectors",) and h["sector"] != sector_filter:
                continue
            live_price = _maybe(h["ticker"], "price", live_prices) or h.get("current_price", 0)
            change_pct = _maybe(h["ticker"], "change_pct", live_prices) or 0
            score      = h.get("final_score", 0)
            action     = h.get("action", "Hold")
            price_str  = fmt_currency(live_price) if live_price else "—"
            rows.append(
                f'<div class="wl-row">'
                f'<div class="wl-c-ticker">{_circle(h["ticker"], h["sector"])}'
                f'<div><div class="wl-ticker-name">{h["ticker"]}</div>'
                f'<div class="wl-company-name">{h["name"]}</div></div></div>'
                f'<div class="wl-c-price">{price_str}</div>'
                f'<div class="wl-c-change">{_change_pill(change_pct, bool(live_price))}</div>'
                f'<div class="wl-c-score">{_score_pill(score)}</div>'
                f'<div class="wl-c-sector">{h["sector"]}</div>'
                f'<div class="wl-c-action">{_act_badge(action)}</div>'
                f'<div class="wl-c-status">{_status_badge("Portfolio")}</div>'
                f'</div>'
            )

    # Watchlist
    if status_filter in ("All", "Watchlist"):
        for s in WATCHLIST:
            if sector_filter not in ("All Sectors",) and s["sector"] != sector_filter:
                continue
            live_price = _maybe(s["ticker"], "price", live_prices) or s.get("price", 0)
            change_pct = _maybe(s["ticker"], "change_pct", live_prices) or 0
            score      = s.get("final_score", 0)
            action     = s.get("action", "Watch")
            price_str  = fmt_currency(live_price) if live_price else "—"
            rows.append(
                f'<div class="wl-row">'
                f'<div class="wl-c-ticker">{_circle(s["ticker"], s["sector"])}'
                f'<div><div class="wl-ticker-name">{s["ticker"]}</div>'
                f'<div class="wl-company-name">{s["name"]}</div></div></div>'
                f'<div class="wl-c-price">{price_str}</div>'
                f'<div class="wl-c-change">{_change_pill(change_pct, bool(live_price))}</div>'
                f'<div class="wl-c-score">{_score_pill(score)}</div>'
                f'<div class="wl-c-sector">{s["sector"]}</div>'
                f'<div class="wl-c-action">{_act_badge(action)}</div>'
                f'<div class="wl-c-status">{_status_badge("Watchlist")}</div>'
                f'</div>'
            )

    # Research pipeline
    if status_filter in ("All", "Research"):
        for r in RESEARCH_WATCHLIST:
            if sector_filter not in ("All Sectors",) and r["sector"] != sector_filter:
                continue
            live_price = _maybe(r["ticker"], "price", live_prices)
            change_pct = _maybe(r["ticker"], "change_pct", live_prices) or 0
            price_str  = fmt_currency(live_price) if live_price else "—"
            rows.append(
                f'<div class="wl-row">'
                f'<div class="wl-c-ticker">{_circle(r["ticker"], r["sector"])}'
                f'<div><div class="wl-ticker-name">{r["ticker"]}</div>'
                f'<div class="wl-company-name">{r["name"]}</div></div></div>'
                f'<div class="wl-c-price">{price_str}</div>'
                f'<div class="wl-c-change">{_change_pill(change_pct, bool(live_price))}</div>'
                f'<div class="wl-c-score">{_score_pill(0)}</div>'
                f'<div class="wl-c-sector">{r["sector"]}</div>'
                f'<div class="wl-c-action">{_act_badge("Watch")}</div>'
                f'<div class="wl-c-status">{_status_badge("Research")}</div>'
                f'</div>'
            )

    if rows:
        _wl_table(header_cols, rows, f"{len(rows)} symbols shown")
    else:
        st.info("No symbols match the selected filters.")


# ── Tab 1: Portfolio ──────────────────────────────────────────────────────────

def _portfolio_tab(live_prices: dict):
    render_section_header(
        "Current Portfolio Holdings",
        "Active positions with live prices and unrealised P&L",
        "💼",
    )

    header_cols = [
        ("Ticker",  "wl-c-ticker"),
        ("Price",   "wl-c-price"),
        ("Today",   "wl-c-change"),
        ("Value",   "wl-c-value"),
        ("P&L %",   "wl-c-pnl"),
        ("Weight",  "wl-c-weight"),
        ("Action",  "wl-c-action"),
    ]

    rows = []
    total_live_value = 0.0

    for h in PORTFOLIO_HOLDINGS:
        pd_data    = live_prices.get(h["ticker"], {})
        live_price = pd_data.get("price") or h["current_price"]
        change_pct = pd_data.get("change_pct", 0) or 0
        mkt_val    = live_price * h["shares"]
        cost       = h["avg_cost"] * h["shares"]
        pnl_pct    = (mkt_val - cost) / cost if cost else 0
        total_live_value += mkt_val

        action    = h.get("action", "Hold")
        price_str = fmt_currency(live_price)
        val_str   = fmt_currency(mkt_val)
        wt_str    = f'{h["current_weight"]:.1f}%'

        rows.append(
            f'<div class="wl-row">'
            f'<div class="wl-c-ticker">{_circle(h["ticker"], h["sector"])}'
            f'<div><div class="wl-ticker-name">{h["ticker"]}</div>'
            f'<div class="wl-company-name">{h["name"]}</div></div></div>'
            f'<div class="wl-c-price">{price_str}</div>'
            f'<div class="wl-c-change">{_change_pill(change_pct, True)}</div>'
            f'<div class="wl-c-value">{val_str}</div>'
            f'<div class="wl-c-pnl">{_pnl_pill(pnl_pct)}</div>'
            f'<div class="wl-c-weight">{wt_str}</div>'
            f'<div class="wl-c-action">{_act_badge(action)}</div>'
            f'</div>'
        )

    cash = PORTFOLIO_SUMMARY["cash"]
    caption = (
        f"{len(PORTFOLIO_HOLDINGS)} positions &nbsp;·&nbsp; "
        f"Invested: {fmt_currency(total_live_value)} &nbsp;·&nbsp; "
        f"Cash: {fmt_currency(cash)} ({PORTFOLIO_SUMMARY['cash_pct']:.1%}) &nbsp;·&nbsp; "
        f"Total: {fmt_currency(total_live_value + cash)}"
    )

    _wl_table(header_cols, rows, caption)


# ── Tab 2: Watchlist ──────────────────────────────────────────────────────────

def _watchlist_tab(live_prices: dict):
    render_section_header(
        "Watchlist",
        "Manually-researched stocks with quality scores and fair values",
        "👁️",
    )

    header_cols = [
        ("Ticker",     "wl-c-ticker"),
        ("Price",      "wl-c-price"),
        ("Today",      "wl-c-change"),
        ("Fair Value", "wl-c-fv"),
        ("Upside",     "wl-c-upside"),
        ("AI Score",   "wl-c-score"),
        ("Action",     "wl-c-action"),
    ]

    rows = []
    for s in WATCHLIST:
        pd_data    = live_prices.get(s["ticker"], {})
        live_price = pd_data.get("price")
        change_pct = pd_data.get("change_pct", 0) or 0

        if live_price:
            price      = live_price
            upside_pct = (s["fair_value"] - live_price) / live_price if s.get("fair_value") else None
        else:
            price      = s.get("price", 0)
            upside_pct = s.get("upside_pct")

        score     = s.get("final_score", 0)
        action    = s.get("action", "Watch")
        fv_str    = fmt_currency(s["fair_value"]) if s.get("fair_value") else "—"
        price_str = fmt_currency(price) if price else "—"

        rows.append(
            f'<div class="wl-row">'
            f'<div class="wl-c-ticker">{_circle(s["ticker"], s["sector"])}'
            f'<div><div class="wl-ticker-name">{s["ticker"]}</div>'
            f'<div class="wl-company-name">{s["name"]}</div></div></div>'
            f'<div class="wl-c-price">{price_str}</div>'
            f'<div class="wl-c-change">{_change_pill(change_pct, bool(live_price))}</div>'
            f'<div class="wl-c-fv">{fv_str}</div>'
            f'<div class="wl-c-upside">{_upside_html(upside_pct)}</div>'
            f'<div class="wl-c-score">{_score_pill(score)}</div>'
            f'<div class="wl-c-action">{_act_badge(action)}</div>'
            f'</div>'
        )

    researched = sum(1 for s in WATCHLIST if s.get("final_score", 0) > 0)
    pending    = len(WATCHLIST) - researched
    caption    = (
        f"{researched} stocks fully researched &nbsp;·&nbsp; {pending} pending. "
        "Open Stock Research to run a live valuation for any stock."
    )
    _wl_table(header_cols, rows, caption)


# ── Tab 3: Research Pipeline ──────────────────────────────────────────────────

def _research_tab(live_prices: dict):
    render_section_header(
        "Research Pipeline",
        "Potential buys tracked at live price — scores pending research",
        "🔭",
    )

    # Sector filter + search (unchanged logic)
    sectors = ["All Sectors"] + sorted({r["sector"] for r in RESEARCH_WATCHLIST})
    col_search, col_sector, _ = st.columns([2, 2, 4], gap="small")
    with col_search:
        search = st.text_input(
            "Search", placeholder="Ticker or company…",
            label_visibility="collapsed", key="rw_search",
        ).upper().strip()
    with col_sector:
        sector_filter = st.selectbox(
            "Sector", sectors,
            label_visibility="collapsed", key="rw_sector",
        )

    filtered = RESEARCH_WATCHLIST
    if search:
        filtered = [r for r in filtered if search in r["ticker"] or search in r["name"].upper()]
    if sector_filter != "All Sectors":
        filtered = [r for r in filtered if r["sector"] == sector_filter]

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    header_cols = [
        ("Ticker", "wl-c-ticker"),
        ("Price",  "wl-c-price"),
        ("Today",  "wl-c-change"),
        ("Sector", "wl-c-sector"),
        ("Status", "wl-c-status"),
    ]

    rows = []
    for r in filtered:
        pd_data    = live_prices.get(r["ticker"], {})
        live_price = pd_data.get("price")
        change_pct = pd_data.get("change_pct", 0) or 0
        price_str  = fmt_currency(live_price) if live_price else "—"

        rows.append(
            f'<div class="wl-row">'
            f'<div class="wl-c-ticker">{_circle(r["ticker"], r["sector"])}'
            f'<div><div class="wl-ticker-name">{r["ticker"]}</div>'
            f'<div class="wl-company-name">{r["name"]}</div></div></div>'
            f'<div class="wl-c-price">{price_str}</div>'
            f'<div class="wl-c-change">{_change_pill(change_pct, bool(live_price))}</div>'
            f'<div class="wl-c-sector">{r["sector"]}</div>'
            f'<div class="wl-c-status">{_status_badge("Research")}</div>'
            f'</div>'
        )

    caption = (
        f"Showing {len(filtered)} of {len(RESEARCH_WATCHLIST)} stocks. "
        "Open Stock Research and type any ticker to run a live valuation."
    )
    _wl_table(header_cols, rows, caption)


# ── Insight cards ─────────────────────────────────────────────────────────────

def _insight_cards(live_prices: dict):
    render_section_header("Insights", "Opportunities, risk flags, and recent movers", "💡")

    col1, col2, col3 = st.columns(3, gap="medium")

    # ── Top Opportunities ─────────────────────────────────────────
    with col1:
        opps = []
        for s in WATCHLIST:
            if not s.get("buy_below") or not s.get("fair_value"):
                continue
            pd_data    = live_prices.get(s["ticker"], {})
            live_price = pd_data.get("price") or s.get("price", 0)
            if not live_price:
                continue
            upside = (s["fair_value"] - live_price) / live_price
            opps.append((s["ticker"], s["name"], upside, s.get("action", "Watch")))
        opps.sort(key=lambda x: x[2], reverse=True)

        rows_html = ""
        for ticker, name, upside, action in opps[:5]:
            col  = "#16A34A" if upside >= 0 else "#DC2626"
            sign = "+" if upside >= 0 else ""
            rows_html += (
                f'<div class="wl-insight-row">'
                f'<span class="wl-insight-ticker">{ticker}</span>'
                f'<span class="wl-insight-name">{name}</span>'
                f'<span style="color:{col};font-weight:600;font-size:13px;white-space:nowrap;">'
                f'{sign}{upside*100:.1f}%</span>'
                f'</div>'
            )
        if not rows_html:
            rows_html = '<div style="font-size:13px;color:#94A3B8;padding:8px 0;">No data yet — add buy-below prices in watchlist.</div>'

        st.markdown(
            f'<div class="wl-insight-card">'
            f'<div class="wl-insight-title">&#127919; Top Opportunities</div>'
            f'{rows_html}</div>',
            unsafe_allow_html=True,
        )

    # ── Highest Concentration ─────────────────────────────────────
    with col2:
        top_holdings = sorted(PORTFOLIO_HOLDINGS, key=lambda h: h["current_weight"], reverse=True)[:5]
        rows_html = ""
        for h in top_holdings:
            wt    = h["current_weight"]
            color = "#DC2626" if wt > 12 else ("#D97706" if wt > 8 else "#475569")
            rows_html += (
                f'<div class="wl-insight-row">'
                f'<span class="wl-insight-ticker">{h["ticker"]}</span>'
                f'<span class="wl-insight-name">{h["name"]}</span>'
                f'<span style="color:{color};font-weight:600;font-size:13px;white-space:nowrap;">'
                f'{wt:.1f}%</span>'
                f'</div>'
            )
        st.markdown(
            f'<div class="wl-insight-card">'
            f'<div class="wl-insight-title">&#9878; Concentration</div>'
            f'{rows_html}</div>',
            unsafe_allow_html=True,
        )

    # ── Recent Movers ─────────────────────────────────────────────
    with col3:
        movers = []
        for ticker, data in live_prices.items():
            if data.get("price") and data.get("change_pct") is not None:
                movers.append((ticker, data["price"], data["change_pct"]))
        movers.sort(key=lambda x: abs(x[2]), reverse=True)

        rows_html = ""
        for ticker, price, chg in movers[:5]:
            col  = "#16A34A" if chg >= 0 else "#DC2626"
            sign = "+" if chg >= 0 else ""
            rows_html += (
                f'<div class="wl-insight-row">'
                f'<span class="wl-insight-ticker">{ticker}</span>'
                f'<span class="wl-insight-name">{fmt_currency(price)}</span>'
                f'<span style="color:{col};font-weight:600;font-size:13px;white-space:nowrap;">'
                f'{sign}{chg:.2f}%</span>'
                f'</div>'
            )
        if not rows_html:
            rows_html = '<div style="font-size:13px;color:#94A3B8;padding:8px 0;">Live price data unavailable.</div>'

        st.markdown(
            f'<div class="wl-insight-card">'
            f'<div class="wl-insight-title">&#9889; Recent Movers</div>'
            f'{rows_html}</div>',
            unsafe_allow_html=True,
        )
