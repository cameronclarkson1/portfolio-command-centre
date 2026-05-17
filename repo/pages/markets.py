"""
markets.py — Markets page (Step 4: wired to live services).

Layout:
  1. Header
  2. Index metric tiles (S&P 500, NASDAQ, Dow, VIX)
  3. Regime card + regime rules (two columns)
  4. Sector performance bar chart
  5. Macro indicators panel
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

from components import (
    render_section_header,
    render_metric_card,
    render_regime_banner,
    html_badge,
    render_html,
    now_str,
)
from utils.formatting import fmt_pct
from services import market_data_service, macro_service


def render():
    _header()
    _index_tiles()
    st.markdown("<br>", unsafe_allow_html=True)
    _regime_section()
    st.markdown("<br>", unsafe_allow_html=True)
    _sector_chart()
    st.markdown("<br>", unsafe_allow_html=True)
    _macro_panel()


# ── Sections ──────────────────────────────────────────────────────────────────

def _header():
    col_title, col_meta = st.columns([5, 1])
    with col_title:
        render_html(
            f'<div style="margin-bottom:4px;"><span style="font-size:22px; font-weight:700; color:#0B0B0F; letter-spacing:-0.02em;">Markets</span></div>'
            f'<div style="font-size:13px; color:#5B6472;">Market environment — indices, regime, sectors, and macro indicators · {datetime.now().strftime("%d %B %Y")}</div>'
        )
    with col_meta:
        render_html(f'<div style="padding-top:14px; text-align:right; font-size:11px; color:#94a3b8;">Updated {now_str()}</div>')
    st.markdown(
        '<div style="height:1px; background:#e2e8f0; margin:14px 0 20px;"></div>',
        unsafe_allow_html=True,
    )


def _index_tiles():
    render_section_header("Major Indices", "Today's performance", "📈")

    indices = market_data_service.get_market_indices()

    if not indices:
        st.warning("Index data unavailable — provider call failed. Check logs.")
        return

    cols = st.columns(len(indices), gap="small")

    for col, idx in zip(cols, indices):
        change   = idx.get("change_pct", 0) or 0
        is_vix   = idx["name"] == "VIX"
        pos_good = not is_vix
        up       = change >= 0
        good_move = up if pos_good else not up
        dtype    = "positive" if good_move else "negative"

        with col:
            render_metric_card(
                label      = idx["name"],
                value      = f"{idx['value']:,.1f}",
                delta      = fmt_pct(change),
                delta_type = dtype,
                icon       = ("😨" if idx["value"] > 25 else "😌") if is_vix else ("📈" if up else "📉"),
            )


def _regime_section():
    render_section_header("Market Regime", "Current environment and portfolio rules", "🌐")

    r = macro_service.get_market_regime()

    if not r:
        st.warning("Regime data unavailable — VIX could not be fetched.")
        return

    buying_rule = r["buying_rule"]
    for emoji in ("🟢 ", "🟡 ", "🔴 ", "🚨 "):
        buying_rule = buying_rule.replace(emoji, "")
    summary_short = r["summary"].split(".")[0] + "."

    render_regime_banner(
        regime      = r["regime"],
        vix         = r["vix"],
        trend       = r["sp500_trend"],
        summary     = summary_short,
        buying_rule = buying_rule,
    )

    # Regime rule grid — four boxes
    regime_rules = {
        "risk-on":  ("🟢 Risk-On",  "#f0fdf4", "#166534",
                     "Normal buying conditions. Full position building allowed. Valuation discipline still applies."),
        "Neutral":  ("🟡 Neutral",  "#fefce8", "#854d0e",
                     "Cautious buying only. Prefer adds over new initiations. Maintain cash target."),
        "risk-off": ("🟠 Risk-Off", "#fff7ed", "#9a3412",
                     "Restrict new buys. Focus on capital preservation. Consider raising cash above target."),
        "crisis":   ("🔴 Crisis",   "#fef2f2", "#991b1b",
                     "Preserve capital only. No aggressive buying. Hold quality positions. Large cash required."),
    }

    cols = st.columns(4, gap="small")
    current = r["regime"]
    for col, (key, (label, bg, colour, desc)) in zip(cols, regime_rules.items()):
        is_current = key == current
        border     = "2px solid " + colour if is_current else "1px solid #e2e8f0"
        shadow     = "box-shadow:0 0 0 3px " + (colour + "33;") if is_current else ""
        with col:
            current_label = f"<div style='margin-top:8px; font-size:11px; font-weight:700; color:{colour};'>▶ CURRENT</div>" if is_current else ""
            render_html(
                f'<div style="background:{bg}; border:{border}; border-radius:10px; padding:14px 16px; {shadow} height:100%;">'
                f'<div style="font-size:13px; font-weight:700; color:{colour}; margin-bottom:6px;">{label}</div>'
                f'<div style="font-size:12px; color:{colour}; opacity:0.85; line-height:1.45;">{desc}</div>'
                f'{current_label}</div>'
            )


def _sector_chart():
    render_section_header("Sector Performance", "Today's % change by sector", "🗂️")

    sector_perf = market_data_service.get_sector_performance()

    if not sector_perf:
        st.warning("Sector data unavailable — provider call failed.")
        return

    data = pd.DataFrame(
        [{"Sector": s, "Change (%)": v} for s, v in sector_perf.items()]
    ).sort_values("Change (%)", ascending=True)

    data["colour"] = data["Change (%)"].apply(
        lambda x: "#10b981" if x >= 0 else "#ef4444"
    )

    bars = (
        alt.Chart(data)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X("Change (%):Q", title="% Change Today",
                    axis=alt.Axis(format=".2f")),
            y=alt.Y("Sector:N", sort=None, title=""),
            color=alt.Color("colour:N", scale=None),
            tooltip=["Sector", alt.Tooltip("Change (%):Q", format="+.2f")],
        )
        .properties(height=300)
    )

    zero_line = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(color="#9ca3af", strokeWidth=1)
        .encode(x="x:Q")
    )

    st.altair_chart(bars + zero_line, use_container_width=True)

    sorted_sectors = sorted(sector_perf.items(), key=lambda x: x[1], reverse=True)
    best  = sorted_sectors[0]
    worst = sorted_sectors[-1]
    st.caption(
        f"Best: **{best[0]}** ({fmt_pct(best[1]/100)})  ·  "
        f"Worst: **{worst[0]}** ({fmt_pct(worst[1]/100)})"
    )


def _macro_panel():
    render_section_header("Macro Indicators", "Treasury yields, rates, and key economic data", "🏛️")

    snapshot   = macro_service.get_macro_snapshot()
    yield_data = macro_service.get_yield_curve_data()

    if not snapshot and not yield_data:
        st.warning("Macro data unavailable — FRED connection failed.")
        return

    # Build metric cards from whatever series returned data
    def _pct_str(val):
        return f"{val:.2f}%" if val is not None else "—"

    def _series_val(series_key):
        if snapshot and series_key in snapshot and snapshot[series_key]:
            return snapshot[series_key].get("value")
        return None

    y10  = yield_data["treasury_10y"] if yield_data else _series_val("treasury_10y")
    y2   = yield_data["treasury_2y"]  if yield_data else _series_val("treasury_2y")
    fed  = _series_val("fed_funds_rate")
    cpi  = _series_val("cpi_yoy")
    unem = _series_val("unemployment")
    gdp  = _series_val("gdp_growth")

    macro_metrics = [
        {"label": "10Y Treasury",   "value": _pct_str(y10),  "icon": "🏛️"},
        {"label": "2Y Treasury",    "value": _pct_str(y2),   "icon": "🏛️"},
        {"label": "Fed Funds Rate", "value": _pct_str(fed),  "icon": "🏦"},
        {"label": "CPI (YoY)",      "value": _pct_str(cpi),  "icon": "📊"},
        {"label": "Unemployment",   "value": _pct_str(unem), "icon": "👷"},
        {"label": "GDP Growth",     "value": _pct_str(gdp),  "icon": "📈"},
    ]

    c1, c2, c3 = st.columns(3, gap="medium")
    for col, m in zip([c1, c2, c3], macro_metrics[:3]):
        with col:
            render_metric_card(label=m["label"], value=m["value"], icon=m["icon"])

    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3, gap="medium")
    for col, m in zip([c4, c5, c6], macro_metrics[3:]):
        with col:
            render_metric_card(label=m["label"], value=m["value"], icon=m["icon"])

    st.markdown("<br>", unsafe_allow_html=True)

    # Yield curve interpretation
    if yield_data:
        spread      = yield_data["spread"]
        status      = yield_data["status"]
        interp      = yield_data["interpretation"]
        badge_style = "sell" if status == "Inverted" else ("hold" if status == "Flat" else "buy")
        spread_badge = html_badge(status, badge_style)

        bg_colour     = "#fef2f2" if status == "Inverted" else ("#fefce8" if status == "Flat" else "#f0fdf4")
        border_colour = "#fecaca" if status == "Inverted" else ("#fef08a" if status == "Flat" else "#bbf7d0")
        text_colour   = "#991b1b" if status == "Inverted" else ("#854d0e" if status == "Flat" else "#166534")

        render_html(
            f'<div style="background:{bg_colour}; border:1px solid {border_colour}; border-radius:10px; padding:14px 18px;">'
            f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">'
            f'<span style="font-size:14px; font-weight:600; color:{text_colour};">Yield Curve</span>{spread_badge}</div>'
            f'<div style="font-size:13px; color:#374151;">{interp}</div></div>'
        )
    elif snapshot:
        st.info("Yield curve detail unavailable — treasury yield fetch failed.")
