"""
app.py — AI HedgeFund entry point.

Run with:
    cd frontend
    python -m streamlit run app.py
"""

import streamlit as st
from datetime import datetime

# ── Page config — must be the very first Streamlit call ───────────────────────
st.set_page_config(
    page_title="AI HedgeFund",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Inject global CSS ─────────────────────────────────────────────────────────
from styles import CSS
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ── Import page modules ───────────────────────────────────────────────────────
import pages.dashboard     as dashboard
import pages.watchlist     as watchlist
import pages.markets       as markets
import pages.intelligence  as intelligence
import pages.portfolio     as portfolio
import pages.stock_research as stock_research
import pages.risk_centre   as risk_centre
import pages.settings      as settings

# ── Navigation definition ─────────────────────────────────────────────────────
# Groups: (group_label, [(display label, module, page key), ...])
NAV_GROUPS = [
    ("RESEARCH", [
        ("🏠  Dashboard",       dashboard,      "dashboard"),
        ("📋  Watchlist",       watchlist,      "watchlist"),
        ("🔍  Stock Research",  stock_research, "stock_research"),
    ]),
    ("MARKET", [
        ("🌍  Markets",         markets,        "markets"),
        ("🧠  Intelligence",    intelligence,   "intelligence"),
    ]),
    ("PORTFOLIO", [
        ("⚖️  Portfolio",       portfolio,      "portfolio"),
        ("🛡️  Risk Centre",     risk_centre,    "risk_centre"),
    ]),
    ("SYSTEM", [
        ("⚙️  Settings",        settings,       "settings"),
    ]),
]

_ALL_PAGES = [(label, mod, key) for _, group in NAV_GROUPS for label, mod, key in group]
_MODULES   = [p[1] for p in _ALL_PAGES]
_KEYS      = [p[2] for p in _ALL_PAGES]

# ── Routing: query params take priority, fallback to session state ────────────
if "page" in st.query_params and st.query_params["page"] in _KEYS:
    st.session_state["nav_page"] = st.query_params["page"]
elif "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "dashboard"


def _get_selected_module() -> object:
    key = st.session_state.get("nav_page", "dashboard")
    for _, pages in NAV_GROUPS:
        for _, module, k in pages:
            if k == key:
                return module
    return _MODULES[0]


def _render_top_nav():
    """Render premium top navigation bar (brand bar + nav button row)."""
    current = st.session_state.get("nav_page", "dashboard")
    now     = datetime.now()

    # Detect approximate market hours (Mon–Fri 9:30–16:00 ET, simplified)
    is_weekday   = now.weekday() < 5
    market_open  = is_weekday and 9 <= now.hour < 16
    status_cls   = "tn-live-open" if market_open else "tn-live-closed"
    status_label = "● Market Open" if market_open else "● Market Closed"

    # Brand bar (full-width dark navy strip)
    st.markdown(
        f'<div class="tn-brand">'
        f'<div style="display:flex;align-items:center;gap:12px;">'
        f'<div class="tn-logo-box">🏛️</div>'
        f'<div><div class="tn-name">AI HedgeFund</div>'
        f'<div class="tn-tagline">Private Market Intelligence</div></div>'
        f'</div>'
        f'<div class="tn-meta">'
        f'<span class="tn-date">{now.strftime("%a %d %b %Y · %H:%M")}</span>'
        f'<span class="{status_cls}">{status_label}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # Nav button row — appears on navy background via nth-child(3) CSS
    NAV_ITEMS = [
        ("Dashboard",    "dashboard"),
        ("Watchlist",    "watchlist"),
        ("Research",     "stock_research"),
        ("Markets",      "markets"),
        ("Intelligence", "intelligence"),
        ("Portfolio",    "portfolio"),
        ("Risk Centre",  "risk_centre"),
        ("Settings",     "settings"),
    ]

    cols = st.columns([1] + [1] * len(NAV_ITEMS) + [3, 0.6])

    for i, (label, key) in enumerate(NAV_ITEMS):
        with cols[i + 1]:
            is_active = current == key
            if st.button(
                label, key=f"tn_{key}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                st.session_state["nav_page"] = key
                st.query_params["page"] = key
                st.rerun()

    with cols[-1]:
        if st.button("↻", key="tn_refresh", use_container_width=True):
            st.rerun()

    st.markdown('<div class="tn-divider"></div>', unsafe_allow_html=True)


def main():
    _render_top_nav()
    _get_selected_module().render()


if __name__ == "__main__":
    main()
