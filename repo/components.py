"""
components.py — Reusable UI components for the Portfolio Command Centre.

Every visual building block is defined here as a function.
Page files import from here — they do not contain raw HTML or CSS.

Naming conventions:
  render_*()  → calls st.markdown() internally, renders to the page
  html_*()    → returns an HTML string (used inside other components)
"""

from __future__ import annotations
import streamlit as st
from datetime import datetime


def _md(html: str) -> None:
    """Render HTML via st.markdown, stripping blank lines that confuse the Markdown parser."""
    import re
    cleaned = re.sub(r"\n[ \t]*\n", "\n", html.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


def _md_sidebar(html: str) -> None:
    import re
    cleaned = re.sub(r"\n[ \t]*\n", "\n", html.strip())
    st.sidebar.markdown(cleaned, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# PAGE LEVEL
# ══════════════════════════════════════════════════════════════════

def render_page_header(title: str, subtitle: str = "", last_updated: str = ""):
    lu  = f'<div class="pcc-page-meta">Last updated: {last_updated}</div>' if last_updated else ""
    sub = f'<div class="pcc-page-subtitle">{subtitle}</div>' if subtitle else ""
    _md(f'<div class="pcc-page-header"><div><div class="pcc-page-title">{title}</div>{sub}</div>{lu}</div>')


def render_section_header(title: str, subtitle: str = "", icon: str = ""):
    icon_part = f"{icon}&nbsp;" if icon else ""
    sub       = f'<div class="pcc-section-subtitle">{subtitle}</div>' if subtitle else ""
    _md(f'<div class="pcc-section-header"><div class="pcc-section-title">{icon_part}{title}</div>{sub}</div>')


def render_placeholder(title: str, body: str, icon: str = "🔧", stage_label: str = "Coming soon"):
    _md(
        f'<div class="pcc-placeholder">'
        f'<div class="pcc-placeholder-icon">{icon}</div>'
        f'<div class="pcc-placeholder-title">{title}</div>'
        f'<div class="pcc-placeholder-body">{body}</div>'
        f'<div class="pcc-placeholder-stage">{stage_label}</div>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════
# METRIC CARDS
# ══════════════════════════════════════════════════════════════════

def render_metric_card(
    label: str,
    value: str,
    delta: str = "",
    delta_type: str = "neutral",   # "positive" | "negative" | "neutral"
    icon: str = "",
    accent: bool = False,
):
    parts = ['<div class="pcc-metric">']
    if accent:
        parts.append('<div class="pcc-metric-accent"></div>')
    if icon:
        parts.append(f'<div class="pcc-metric-icon">{icon}</div>')
    parts.append(f'<div class="pcc-metric-label">{label}</div>')
    parts.append(f'<div class="pcc-metric-value">{value}</div>')
    if delta:
        delta_cls = {
            "positive": "pcc-delta-pos",
            "negative": "pcc-delta-neg",
            "neutral":  "pcc-delta-neu",
            "warning":  "pcc-delta-warn",
        }.get(delta_type, "pcc-delta-neu")
        arrow = "▲ " if delta_type == "positive" else ("▼ " if delta_type == "negative" else "")
        parts.append(f'<div class="pcc-metric-delta {delta_cls}">{arrow}{delta}</div>')
    parts.append('</div>')
    _md("".join(parts))


# ══════════════════════════════════════════════════════════════════
# BADGES  (return HTML strings — used inside other components)
# ══════════════════════════════════════════════════════════════════

def html_badge(text: str, variant: str = "hold") -> str:
    css = f"pcc-badge pcc-badge-{variant.lower().replace(' ', '-')}"
    return f'<span class="{css}">{text}</span>'


# ══════════════════════════════════════════════════════════════════
# DECISION CARDS
# ══════════════════════════════════════════════════════════════════

_DECISION_BORDER = {
    "Buy":   "#16A34A",
    "Add":   "#102A4C",
    "Hold":  "#9ca3af",
    "Watch": "#B45309",
    "Trim":  "#f97316",
    "Sell":  "#DC2626",
    "Avoid": "#6b7280",
}


def render_decision_card(
    ticker: str,
    name: str,
    action: str,
    score: int,
    reason: str,
    confidence: str = "",
):
    border    = _DECISION_BORDER.get(action, "#9ca3af")
    badge     = html_badge(action, action.lower())
    conf_html = f'<span style="font-size:11px;color:#9ca3af;">&nbsp;{confidence}</span>' if confidence else ""
    bar       = html_score_bar(score)
    _md(
        f'<div class="pcc-decision" style="border-left-color:{border};">'
        f'<div class="pcc-decision-header">'
        f'<span class="pcc-decision-ticker">{ticker}</span>'
        f'<span class="pcc-decision-name">{name}</span>'
        f'<span style="margin-left:auto;display:flex;align-items:center;gap:6px;">{badge}{conf_html}</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
        f'<span class="pcc-decision-score">{score}/100</span>'
        f'<div style="flex:1;max-width:100px;">{bar}</div>'
        f'</div>'
        f'<div class="pcc-decision-reason">{reason}</div>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════
# RISK ALERT CARDS
# ══════════════════════════════════════════════════════════════════

_ALERT_ICON = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}


def render_risk_alert(
    message: str,
    level: str = "warning",
    recommended_action: str = "",
):
    icon        = _ALERT_ICON.get(level, "⚠️")
    action_html = (
        f'<div class="pcc-alert-action pcc-alert-action-{level}">→ {recommended_action}</div>'
        if recommended_action else ""
    )
    _md(
        f'<div class="pcc-alert pcc-alert-{level}">'
        f'<span class="pcc-alert-icon">{icon}</span>'
        f'<div class="pcc-alert-body">'
        f'<div class="pcc-alert-message">{message}</div>'
        f'{action_html}'
        f'</div>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════
# MARKET REGIME BANNER
# ══════════════════════════════════════════════════════════════════

_REGIME_ICON  = {"risk-on": "🟢", "Neutral": "🟡", "risk-off": "🟠", "crisis": "🔴"}
_REGIME_CSS   = {"risk-on": "risk-on", "Neutral": "neutral", "risk-off": "risk-off", "crisis": "crisis"}
_REGIME_BADGE = {"risk-on": "risk-on", "Neutral": "neutral", "risk-off": "risk-off", "crisis": "critical"}


def render_regime_banner(regime: str, vix: float, trend: str, summary: str, buying_rule: str):
    icon       = _REGIME_ICON.get(regime, "⚪")
    css_suffix = _REGIME_CSS.get(regime, "neutral")
    badge      = html_badge(regime, _REGIME_BADGE.get(regime, "neutral"))
    _md(
        f'<div class="pcc-regime pcc-regime-{css_suffix}">'
        f'<div class="pcc-regime-icon">{icon}</div>'
        f'<div class="pcc-regime-body">'
        f'<div class="pcc-regime-title">{regime} — {buying_rule}</div>'
        f'<div class="pcc-regime-detail">VIX {vix:.1f} · S&P {trend} · {summary}</div>'
        f'</div>'
        f'<div class="pcc-regime-badge">{badge}</div>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════
# SCORE BARS
# ══════════════════════════════════════════════════════════════════

def html_score_bar(score: int, max_score: int = 100) -> str:
    pct = int(min(100, max(0, score)) / max_score * 100)
    cls = "pcc-score-fill-green" if score >= 70 else ("pcc-score-fill-amber" if score >= 50 else "pcc-score-fill-red")
    return f'<div class="pcc-score-bar"><div class="pcc-score-fill {cls}" style="width:{pct}%;"></div></div>'


def render_score_bar(label: str, score: int, max_score: int = 100):
    pct      = int(min(100, max(0, score)) / max_score * 100)
    fill_cls = "pcc-score-fill-green" if score >= 70 else ("pcc-score-fill-amber" if score >= 50 else "pcc-score-fill-red")
    num_cls  = "pcc-score-num-green"  if score >= 70 else ("pcc-score-num-amber"  if score >= 50 else "pcc-score-num-red")
    _md(
        f'<div class="pcc-score-wrap">'
        f'<div class="pcc-score-label-row">'
        f'<span class="pcc-score-label">{label}</span>'
        f'<span class="pcc-score-num {num_cls}">{score}</span>'
        f'</div>'
        f'<div class="pcc-score-bar"><div class="pcc-score-fill {fill_cls}" style="width:{pct}%;"></div></div>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════
# OPPORTUNITY ROWS
# ══════════════════════════════════════════════════════════════════

def render_opportunity_row(
    rank: int,
    ticker: str,
    name: str,
    price: str,
    upside_pct: float,
    score: int,
    action: str,
):
    up_str = f"+{upside_pct*100:.1f}%" if upside_pct >= 0 else f"{upside_pct*100:.1f}%"
    up_cls = "pcc-opp-up-pos" if upside_pct >= 0 else "pcc-opp-up-neg"
    badge  = html_badge(action, action.lower())
    _md(
        f'<div class="pcc-opp-item">'
        f'<span class="pcc-opp-rank">#{rank}</span>'
        f'<span class="pcc-opp-ticker">{ticker}</span>'
        f'<span class="pcc-opp-name">{name}</span>'
        f'<span class="pcc-opp-price">{price}</span>'
        f'<span class="{up_cls}">{up_str}</span>'
        f'<span class="pcc-opp-score">{score}/100</span>'
        f'{badge}'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════
# SIDEBAR COMPONENTS
# ══════════════════════════════════════════════════════════════════

def render_sidebar_stat(
    label: str,
    value: str,
    delta: str = "",
    delta_type: str = "neutral",
):
    delta_cls  = {"positive": "pcc-sd-pos", "negative": "pcc-sd-neg", "neutral": "pcc-sd-neu"}.get(delta_type, "pcc-sd-neu")
    delta_html = f'<div class="pcc-sidebar-delta {delta_cls}">{delta}</div>' if delta else ""
    _md_sidebar(
        f'<div class="pcc-sidebar-block">'
        f'<div class="pcc-sidebar-label">{label}</div>'
        f'<div class="pcc-sidebar-value">{value}</div>'
        f'{delta_html}'
        f'</div>'
    )


def render_sidebar_regime(regime: str, vix: float):
    icons   = {"risk-on": "🟢", "Neutral": "🟡", "risk-off": "🟠", "crisis": "🔴"}
    colours = {"risk-on": "#4ade80", "Neutral": "#fde047", "risk-off": "#fb923c", "crisis": "#f87171"}
    icon    = icons.get(regime, "⚪")
    colour  = colours.get(regime, "#64748b")
    _md_sidebar(
        f'<div class="pcc-sidebar-block">'
        f'<div class="pcc-sidebar-label">Market Regime</div>'
        f'<div style="font-size:15px;font-weight:700;color:{colour};margin-top:3px;">{icon} {regime}</div>'
        f'<div class="pcc-sidebar-delta pcc-sd-neu">VIX {vix:.1f}</div>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════
# UTILITY
# ══════════════════════════════════════════════════════════════════

def now_str() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")


def render_html(html: str) -> None:
    """Public helper for page files: renders HTML safely without blank-line parsing bugs."""
    _md(html)
