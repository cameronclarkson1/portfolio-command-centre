"""
settings.py — Settings & Configuration page.

Settings persist to storage/user_settings.json and survive browser refresh / app restart.
On load: reads from file first, falls back to hardcoded defaults.
On save: writes all cfg_* keys to file.
"""

import streamlit as st
import json
import pathlib
from datetime import datetime
from components import render_section_header, html_badge, now_str

_SETTINGS_FILE = pathlib.Path(__file__).parent.parent / "storage" / "user_settings.json"

_DEFAULTS = {
    "pos_limit":     10.0,
    "sector_cap":    30.0,
    "cash_target":   10.0,
    "cash_min":       5.0,
    "cash_max":      20.0,
    "max_positions": 15,
    "w_quality":     25,
    "w_valuation":   30,
    "w_growth":      20,
    "w_momentum":    15,
    "w_risk":        10,
    "min_trade":     500,
    "rebal_band":     2.0,
    "beta_min":       0.8,
    "beta_max":       1.2,
    "currency":      "USD",
    "date_fmt":      "DD/MM/YYYY",
}


def _load_saved() -> dict:
    try:
        if _SETTINGS_FILE.exists():
            with open(_SETTINGS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_settings() -> bool:
    try:
        data = {k: st.session_state.get(f"cfg_{k}", v) for k, v in _DEFAULTS.items()}
        data["_saved_at"] = datetime.now().isoformat()
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Could not save settings: {e}")
        return False


def _init():
    # Load from file exactly once per browser session
    if "cfg_loaded_from_file" not in st.session_state:
        saved = _load_saved()
        st.session_state["cfg_loaded_from_file"] = True
        for k, v in _DEFAULTS.items():
            if f"cfg_{k}" not in st.session_state:
                st.session_state[f"cfg_{k}"] = saved.get(k, v)
        if "_saved_at" in saved:
            st.session_state["_settings_saved_at"] = saved["_saved_at"]
    else:
        # Subsequent renders: only fill missing keys
        for k, v in _DEFAULTS.items():
            if f"cfg_{k}" not in st.session_state:
                st.session_state[f"cfg_{k}"] = v


def render():
    _init()
    _header()
    _portfolio_targets()
    st.markdown("<br>", unsafe_allow_html=True)
    _score_weights()
    st.markdown("<br>", unsafe_allow_html=True)
    _rebalance_thresholds()
    st.markdown("<br>", unsafe_allow_html=True)
    _display_preferences()
    st.markdown("<br>", unsafe_allow_html=True)
    _about()


# ── Sections ──────────────────────────────────────────────────────────────────

def _header():
    st.markdown(
        f'<div style="margin-bottom:4px;">'
        f'<span style="font-size:22px;font-weight:700;color:#0B0B0F;letter-spacing:-0.02em;">Settings</span>'
        f'</div>'
        f'<div style="font-size:13px;color:#5B6472;">'
        f'Portfolio targets, score weights, rebalance thresholds, and preferences'
        f' · {datetime.now().strftime("%d %B %Y")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height:1px;background:#E2E8F0;margin:14px 0 20px;"></div>', unsafe_allow_html=True)


def _portfolio_targets():
    render_section_header("Portfolio Targets", "Position size limits, cash buffers, and concentration rules", "🎯")

    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown("**Position & Concentration**")
        st.session_state["cfg_pos_limit"] = st.slider(
            "Max position size (%)", 5.0, 20.0,
            float(st.session_state["cfg_pos_limit"]), 0.5,
            help="Hard cap: no single stock may exceed this % of portfolio value.",
            key="sl_pos_limit",
        )
        st.session_state["cfg_sector_cap"] = st.slider(
            "Sector hard cap (%)", 15.0, 50.0,
            float(st.session_state["cfg_sector_cap"]), 1.0,
            help="No single GICS sector may exceed this % weight.",
            key="sl_sector_cap",
        )
        st.session_state["cfg_max_positions"] = st.number_input(
            "Max open positions", 5, 40,
            int(st.session_state["cfg_max_positions"]), 1,
            key="ni_max_positions",
        )

    with col_b:
        st.markdown("**Cash Management**")
        st.session_state["cfg_cash_target"] = st.slider(
            "Cash target (%)", 0.0, 30.0,
            float(st.session_state["cfg_cash_target"]), 0.5,
            key="sl_cash_target",
        )
        st.session_state["cfg_cash_min"] = st.slider(
            "Cash minimum (%)", 0.0, 15.0,
            float(st.session_state["cfg_cash_min"]), 0.5,
            key="sl_cash_min",
        )
        st.session_state["cfg_cash_max"] = st.slider(
            "Cash maximum (%)", 10.0, 40.0,
            float(st.session_state["cfg_cash_max"]), 1.0,
            key="sl_cash_max",
        )

    pos   = st.session_state["cfg_pos_limit"]
    sec   = st.session_state["cfg_sector_cap"]
    c_tgt = st.session_state["cfg_cash_target"]
    c_min = st.session_state["cfg_cash_min"]
    c_max = st.session_state["cfg_cash_max"]
    mxp   = st.session_state["cfg_max_positions"]

    st.markdown(
        f'<div style="background:#F5F7FA;border:1px solid #E2E8F0;border-radius:10px;'
        f'padding:14px 18px;margin-top:8px;">'
        f'<div style="font-size:10px;color:#94a3b8;text-transform:uppercase;'
        f'letter-spacing:0.06em;margin-bottom:10px;font-weight:600;">Current Rules Summary</div>'
        f'<div style="display:flex;gap:24px;flex-wrap:wrap;">'
        f'<div><span style="font-size:11px;color:#5B6472;">Max position</span><br>'
        f'<span style="font-size:16px;font-weight:700;color:#0B0B0F;">{pos:.1f}%</span></div>'
        f'<div><span style="font-size:11px;color:#5B6472;">Sector cap</span><br>'
        f'<span style="font-size:16px;font-weight:700;color:#0B0B0F;">{sec:.0f}%</span></div>'
        f'<div><span style="font-size:11px;color:#5B6472;">Cash range</span><br>'
        f'<span style="font-size:16px;font-weight:700;color:#0B0B0F;">{c_min:.0f}%–{c_max:.0f}%</span></div>'
        f'<div><span style="font-size:11px;color:#5B6472;">Cash target</span><br>'
        f'<span style="font-size:16px;font-weight:700;color:#0B0B0F;">{c_tgt:.1f}%</span></div>'
        f'<div><span style="font-size:11px;color:#5B6472;">Max positions</span><br>'
        f'<span style="font-size:16px;font-weight:700;color:#0B0B0F;">{mxp}</span></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _score_weights():
    render_section_header("Score Weights", "How much each dimension contributes to the composite score", "⚖️")

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    labels = ["w_quality", "w_valuation", "w_growth", "w_momentum", "w_risk"]
    names  = ["Quality",   "Valuation",   "Growth",   "Momentum",   "Risk"]
    cols   = [c1, c2, c3, c4, c5]

    for col, key, name in zip(cols, labels, names):
        with col:
            st.session_state[f"cfg_{key}"] = st.number_input(
                f"{name} (%)", 0, 60,
                int(st.session_state[f"cfg_{key}"]), 5,
                key=f"ni_{key}",
            )

    total    = sum(st.session_state[f"cfg_{k}"] for k in labels)
    total_ok = total == 100
    colour_map = {
        "w_quality":   "#061A33",
        "w_valuation": "#16A34A",
        "w_growth":    "#B45309",
        "w_momentum":  "#8b5cf6",
        "w_risk":      "#DC2626",
    }
    bars_html = ""
    for k, name in zip(labels, names):
        w   = st.session_state[f"cfg_{k}"]
        pct = (w / max(total, 1)) * 100
        bars_html += (
            f'<div style="margin-bottom:6px;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
            f'<span style="font-size:12px;color:#5B6472;">{name}</span>'
            f'<span style="font-size:12px;font-weight:600;color:#374151;">{w}%</span></div>'
            f'<div style="height:5px;background:#E2E8F0;border-radius:3px;overflow:hidden;">'
            f'<div style="width:{pct:.1f}%;height:100%;background:{colour_map[k]};border-radius:3px;"></div>'
            f'</div></div>'
        )

    t_colour = "#16A34A" if total_ok else "#DC2626"
    t_label  = "Weights sum to 100% ✓" if total_ok else f"Weights sum to {total}% — must equal 100%"
    st.markdown(
        f'<div style="background:#F5F7FA;border:1px solid #E2E8F0;border-radius:10px;'
        f'padding:16px 18px;margin-top:12px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        f'<div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;font-weight:600;">Weight Distribution</div>'
        f'<div style="font-size:12px;font-weight:700;color:{t_colour};">{t_label}</div></div>'
        f'{bars_html}</div>',
        unsafe_allow_html=True,
    )
    if not total_ok:
        st.warning(f"Score weights total {total}%. Adjust to reach exactly 100% before saving.")


def _rebalance_thresholds():
    render_section_header("Rebalance Thresholds", "When to trigger trades and what beta range to target", "🔄")

    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown("**Trade Triggers**")
        st.session_state["cfg_rebal_band"] = st.slider(
            "Rebalance band (%)", 0.5, 5.0,
            float(st.session_state["cfg_rebal_band"]), 0.25,
            help="Trigger a trade when a position drifts this far from its target weight.",
            key="sl_rebal_band",
        )
        st.session_state["cfg_min_trade"] = st.number_input(
            "Minimum trade size ($)", 100, 10000,
            int(st.session_state["cfg_min_trade"]), 100,
            key="ni_min_trade",
        )
    with col_b:
        st.markdown("**Beta Target**")
        st.session_state["cfg_beta_min"] = st.slider(
            "Beta target — lower bound", 0.3, 1.0,
            float(st.session_state["cfg_beta_min"]), 0.05,
            key="sl_beta_min",
        )
        st.session_state["cfg_beta_max"] = st.slider(
            "Beta target — upper bound", 1.0, 2.0,
            float(st.session_state["cfg_beta_max"]), 0.05,
            key="sl_beta_max",
        )

    b_min = st.session_state["cfg_beta_min"]
    b_max = st.session_state["cfg_beta_max"]
    band  = st.session_state["cfg_rebal_band"]
    trade = st.session_state["cfg_min_trade"]
    st.markdown(
        f'<div style="background:#F5F7FA;border:1px solid #E2E8F0;border-radius:10px;'
        f'padding:14px 18px;margin-top:8px;">'
        f'<div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px;font-weight:600;">Threshold Summary</div>'
        f'<div style="display:flex;gap:24px;flex-wrap:wrap;">'
        f'<div><span style="font-size:11px;color:#5B6472;">Beta target</span><br>'
        f'<span style="font-size:16px;font-weight:700;color:#0B0B0F;">{b_min:.2f}–{b_max:.2f}</span></div>'
        f'<div><span style="font-size:11px;color:#5B6472;">Rebalance band</span><br>'
        f'<span style="font-size:16px;font-weight:700;color:#0B0B0F;">±{band:.2f}%</span></div>'
        f'<div><span style="font-size:11px;color:#5B6472;">Min trade</span><br>'
        f'<span style="font-size:16px;font-weight:700;color:#0B0B0F;">${trade:,}</span></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _display_preferences():
    render_section_header("Display Preferences", "Number formatting and date display options", "🖥️")

    col_a, col_b, col_c = st.columns(3, gap="large")
    with col_a:
        st.session_state["cfg_currency"] = st.selectbox(
            "Currency",
            options=["USD", "GBP", "EUR", "AUD", "CAD"],
            index=["USD", "GBP", "EUR", "AUD", "CAD"].index(
                st.session_state.get("cfg_currency", "USD")
            ),
            key="sb_currency",
        )
    with col_b:
        formats = ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"]
        st.session_state["cfg_date_fmt"] = st.selectbox(
            "Date format",
            options=formats,
            index=formats.index(st.session_state.get("cfg_date_fmt", "DD/MM/YYYY")),
            key="sb_date_fmt",
        )
    with col_c:
        st.markdown("**Theme**")
        st.caption("Light theme is enforced via CSS. Streamlit's built-in theme selector is disabled.")

    st.markdown("<br>", unsafe_allow_html=True)

    col_save, col_reset, col_spacer = st.columns([1, 1, 4])
    with col_save:
        if st.button("💾  Save Settings", type="primary", use_container_width=True):
            if _save_settings():
                st.session_state["_settings_saved_at"] = datetime.now().isoformat()
                st.success("✅ Settings saved — they will persist after refresh.")
    with col_reset:
        if st.button("↺  Reset to Defaults", use_container_width=True):
            for k, v in _DEFAULTS.items():
                st.session_state[f"cfg_{k}"] = v
            # Clear saved file
            try:
                if _SETTINGS_FILE.exists():
                    _SETTINGS_FILE.unlink()
            except Exception:
                pass
            st.session_state.pop("_settings_saved_at", None)
            st.rerun()

    saved_at = st.session_state.get("_settings_saved_at")
    if saved_at:
        try:
            dt = datetime.fromisoformat(saved_at)
            st.caption(f"Last saved: {dt.strftime('%d %b %Y at %H:%M')}")
        except Exception:
            pass


def _about():
    render_section_header("About", "Version info and build status", "ℹ️")

    stages = [
        ("Stage 1", "Component library, CSS design system, all 8 pages",                 "complete"),
        ("Stage 2", "Provider layer — Polygon, Finnhub, FMP, yfinance, FRED, SEC EDGAR", "complete"),
        ("Stage 3", "Service layer — caching, fallbacks, confidence scoring",             "complete"),
        ("Stage 4", "Live data wiring — all pages connected to real market data",         "complete"),
        ("Stage 5", "AI analyst layer — Claude API summaries and thesis monitoring",      "planned"),
        ("Stage 6", "Alerts, scheduled scans, email / push notifications",                "planned"),
        ("Stage 7", "Authentication, multi-portfolio, persistent settings",               "planned"),
    ]
    badge_variant = {"complete": "buy", "planned": "hold", "in-progress": "watch"}

    for stage, desc, status in stages:
        badge = html_badge(status.capitalize(), badge_variant.get(status, "hold"))
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;padding:9px 0;'
            f'border-bottom:1px solid #F5F7FA;">'
            f'<div style="font-size:13px;font-weight:700;color:#374151;min-width:70px;">{stage}</div>'
            f'<div style="flex:1;font-size:13px;color:#5B6472;">{desc}</div>'
            f'<div>{badge}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div style="background:#F5F7FA;border:1px solid #E2E8F0;border-radius:10px;padding:14px 18px;">'
        '<div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:6px;">AI HedgeFund — v2.0</div>'
        '<div style="font-size:12px;color:#94a3b8;line-height:1.6;">'
        'Built with Python · Streamlit · Altair · Plotly<br>'
        'AI analysis layer powered by Claude (Anthropic)<br>'
        'All scoring and decision logic is deterministic Python — not AI-generated.'
        '</div></div>',
        unsafe_allow_html=True,
    )
