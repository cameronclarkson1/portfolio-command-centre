"""
stock_research.py — Stock Research page (Stage 4 live data connection).

Deep-dive view for any ticker across five tabs:
  Overview · Valuation · Scores · Risks · Thesis

For watchlist stocks with manual profiles: uses researched fair values, thesis, and risks.
For any other ticker: auto-calculates fair value (DCF), scores, and risk flags from live data.
"""

import streamlit as st

from components import (
    render_section_header,
    render_metric_card,
    render_score_bar,
    html_badge,
    render_html,
    now_str,
)
from utils.sample_data import PORTFOLIO_HOLDINGS, WATCHLIST, RESEARCH_WATCHLIST
from utils.formatting import fmt_currency, fmt_pct
from services import market_data_service, fundamentals_service, news_service
from services import valuation_engine
from datetime import datetime

# ── Extended research profiles (manually written — highest quality data) ───────
_PROFILES = {
    "GOOGL": {
        "full_name":   "Alphabet Inc.",
        "description": (
            "Alphabet is the parent company of Google, the world's dominant search engine. "
            "Revenue streams include Google Search, YouTube, Google Cloud, and hardware devices. "
            "The business generates exceptional free cash flow and is deploying AI (Gemini) "
            "aggressively across its product suite."
        ),
        "fair_value_range": {"Conservative": 165, "Base": 195, "Optimistic": 235},
        "key_assumptions":  {"WACC": "9.2%", "Terminal growth": "3.5%", "Revenue CAGR (5yr)": "12%", "FCF margin": "24%"},
        "models_used":      ["DCF (40%)", "EV/FCF (35%)", "Forward P/E (25%)"],
        "thesis": [
            ("90%+ global search market share — structural moat", True),
            ("Google Cloud growing 28% YoY with margin expansion", True),
            ("YouTube advertising underpenetrated vs viewer hours", True),
            ("Gemini AI integration strengthening product ecosystem", True),
            ("Strong FCF funding buybacks ($70B+ authorised)", True),
            ("Regulatory / antitrust risk is manageable short-term", False),
        ],
        "risks": [
            ("Antitrust & regulatory",   "US DOJ and EU actions may force structural changes to Search.", "critical"),
            ("AI search disruption",     "ChatGPT and AI-native search tools could erode query volume.", "warning"),
            ("Ad revenue cyclicality",   "Digital advertising is sensitive to macroeconomic downturns.",  "warning"),
            ("Cloud competition",        "AWS and Azure both hold larger market shares in cloud.",        "info"),
        ],
        "thesis_status": "Intact",
        "dividend_yield": None,
    },
    "AMZN": {
        "full_name":   "Amazon.com Inc.",
        "description": (
            "Amazon operates the world's largest e-commerce marketplace and cloud infrastructure "
            "platform (AWS). AWS generates the majority of operating profit and is growing at "
            "17%+ YoY. Advertising is a rapidly expanding high-margin revenue stream."
        ),
        "fair_value_range": {"Conservative": 190, "Base": 226, "Optimistic": 275},
        "key_assumptions":  {"WACC": "9.8%", "Terminal growth": "3.0%", "Revenue CAGR (5yr)": "14%", "FCF margin": "18%"},
        "models_used":      ["DCF (35%)", "EV/EBITDA (35%)", "Revenue Multiple (30%)"],
        "thesis": [
            ("AWS is the #1 cloud platform — durable competitive moat", True),
            ("Advertising segment growing 20%+ with high margins", True),
            ("Prime flywheel locks in ~200M high-value subscribers", True),
            ("FCF turning strongly positive after heavy capex cycle", True),
            ("International e-commerce still early in profitability ramp", True),
            ("Retail margins remain thin and vulnerable to competition", False),
        ],
        "risks": [
            ("AWS margin pressure",  "Azure and Google Cloud pricing competition could compress AWS margins.", "warning"),
            ("Regulatory scrutiny",  "Antitrust investigations into marketplace practices in US and EU.",     "warning"),
            ("Capex requirements",   "AI infrastructure spending is accelerating — FCF may disappoint.",     "info"),
            ("Retail profitability", "Core retail generates minimal margins; any slowdown hits hard.",        "info"),
        ],
        "thesis_status": "Intact",
        "dividend_yield": None,
    },
    "MSFT": {
        "full_name":   "Microsoft Corporation",
        "description": (
            "Microsoft is the world's largest software company, with dominant positions in "
            "productivity software (Office 365), cloud infrastructure (Azure), gaming (Xbox), "
            "and enterprise tools (Teams, Dynamics). Azure is growing at 30%+ YoY."
        ),
        "fair_value_range": {"Conservative": 285, "Base": 340, "Optimistic": 400},
        "key_assumptions":  {"WACC": "8.5%", "Terminal growth": "3.5%", "Revenue CAGR (5yr)": "14%", "FCF margin": "35%"},
        "models_used":      ["DCF (40%)", "Quality P/E (35%)", "EV/FCF (25%)"],
        "thesis": [
            ("Azure cloud platform growing 30%+ with sticky enterprise clients", True),
            ("Office 365 / Teams creates deep switching costs for enterprises", True),
            ("Copilot AI monetisation adds $10–30 per seat per month upside", True),
            ("LinkedIn and gaming diversify revenue beyond core cloud + Office", True),
            ("Best-in-class FCF conversion and shareholder return track record", True),
            ("Current price exceeds fair value — no margin of safety", False),
        ],
        "risks": [
            ("Valuation risk",      "Trades above fair value — limited margin of safety.",           "warning"),
            ("Azure growth decel",  "Any slowdown in Azure growth would compress the valuation.",    "warning"),
            ("AI competition",      "OpenAI dependency and Google/Amazon AI competition are headwinds.", "info"),
            ("Regulatory risk",     "Activision integration under regulatory scrutiny in some regions.", "info"),
        ],
        "thesis_status": "Intact",
        "dividend_yield": "0.7%",
    },
    "JNJ": {
        "full_name":   "Johnson & Johnson",
        "description": (
            "Johnson & Johnson is a leading pharmaceutical and medical device company following "
            "the 2023 spin-off of its consumer health division (Kenvue). The company focuses on "
            "innovative medicines and MedTech with a 60-year dividend growth track record."
        ),
        "fair_value_range": {"Conservative": 148, "Base": 166, "Optimistic": 192},
        "key_assumptions":  {"WACC": "8.0%", "Terminal growth": "2.5%", "Revenue CAGR (5yr)": "5%", "FCF margin": "28%"},
        "models_used":      ["DCF (35%)", "DDM (30%)", "EV/EBITDA (35%)"],
        "thesis": [
            ("60+ consecutive years of dividend growth — Dividend King", True),
            ("Strong MedTech pipeline with robotics and surgical platforms", True),
            ("Pharmaceutical pipeline includes oncology and immunology leaders", True),
            ("Balance sheet is fortress-grade with AAA credit rating", True),
            ("Currently trading below fair value — margin of safety present", True),
            ("Talc litigation overhang creates ongoing headline risk", False),
        ],
        "risks": [
            ("Talc litigation",    "Ongoing litigation could result in significant settlements.", "warning"),
            ("Patent cliffs",      "Key drug patents expiring 2025–2028 will face biosimilar competition.", "warning"),
            ("Slow growth",        "Revenue growth expected at 5–6% — below tech sector peers.",  "info"),
            ("FX headwinds",       "International revenues sensitive to US dollar strength.",     "info"),
        ],
        "thesis_status": "Intact",
        "dividend_yield": "3.1%",
    },
    "VZ": {
        "full_name":   "Verizon Communications",
        "description": (
            "Verizon is the largest US wireless carrier by revenue, operating 4G LTE and 5G "
            "networks across the United States. Revenue is primarily subscription-based, "
            "providing stable but slow-growing cash flows. The dividend yield is 6.8%."
        ),
        "fair_value_range": {"Conservative": 36, "Base": 42, "Optimistic": 50},
        "key_assumptions":  {"WACC": "7.5%", "Terminal growth": "1.5%", "Revenue CAGR (5yr)": "2%", "FCF margin": "16%"},
        "models_used":      ["DDM (50%)", "DCF (30%)", "EV/EBITDA (20%)"],
        "thesis": [
            ("6.8% dividend yield — income generation at scale", True),
            ("5G network investment nearing completion — capex to decline", True),
            ("Subscription model provides revenue stability", True),
            ("Subscriber growth has missed estimates 3 consecutive quarters", False),
            ("FCF coverage of dividend is tightening — watch carefully", False),
            ("Debt load is elevated — limits strategic flexibility", False),
        ],
        "risks": [
            ("Dividend sustainability",  "FCF coverage tightening — dividend could be under pressure.", "critical"),
            ("Subscriber losses",        "Three consecutive quarters of net subscriber misses.",         "warning"),
            ("Debt burden",              "High leverage limits ability to invest in network or M&A.",    "warning"),
            ("Competition",              "T-Mobile aggressively taking share with competitive pricing.",  "info"),
        ],
        "thesis_status": "Weakening",
        "dividend_yield": "6.8%",
    },
}

_DEFAULT_PROFILE = {
    "full_name":        None,
    "description":      None,
    "fair_value_range": {},
    "key_assumptions":  {},
    "models_used":      [],
    "thesis":           [],
    "risks":            [],
    "thesis_status":    "—",
    "dividend_yield":   None,
}

_WL_BY_TICKER = {s["ticker"]: s for s in WATCHLIST}


# ── Score calculation from live data ──────────────────────────────────────────

def _calculate_scores(ratios: dict, valuation: dict, price: float) -> dict:
    """Auto-calculate investment scores from live financial ratios and valuation engine output."""
    r = ratios or {}

    # Quality: ROIC + ROE (higher = better business)
    q_factors = []
    roic = r.get("roic")
    if roic is not None:
        q_factors.append(min(100, max(0, int(roic * 400))))   # 25% ROIC → 100
    roe = r.get("roe")
    if roe is not None:
        q_factors.append(min(100, max(0, int(roe * 333))))    # 30% ROE → 100
    quality = int(sum(q_factors) / len(q_factors)) if q_factors else 50

    # Valuation: upside to blended fair value from valuation engine
    fv = (valuation or {}).get("fair_value_base")
    if fv and price:
        upside = (fv - price) / price
        if upside > 0.30:    valuation = 90
        elif upside > 0.15:  valuation = 75
        elif upside > 0.05:  valuation = 62
        elif upside > 0:     valuation = 52
        elif upside > -0.10: valuation = 42
        elif upside > -0.25: valuation = 28
        else:                valuation = 15
    else:
        valuation = 50

    # Growth: revenue growth YoY
    growth_rate = r.get("revenue_growth_yoy")
    if growth_rate is not None:
        if growth_rate > 0.25:    growth = 92
        elif growth_rate > 0.15:  growth = 80
        elif growth_rate > 0.08:  growth = 65
        elif growth_rate > 0.03:  growth = 50
        elif growth_rate > 0:     growth = 38
        else:                     growth = 22
    else:
        growth = 50

    # Momentum: position in 52-week range (contrarian — near low = good entry)
    high = r.get("52_week_high")
    low  = r.get("52_week_low")
    if high and low and price and high > low:
        position = (price - low) / (high - low)   # 0 = at low, 1 = at high
        momentum = int(75 - position * 40)         # 35–75 range
    else:
        momentum = 50

    # Risk: beta (lower = safer = higher score) minus debt penalty
    beta = r.get("beta")
    if beta is not None:
        if beta < 0.5:    risk_base = 88
        elif beta < 0.8:  risk_base = 78
        elif beta < 1.1:  risk_base = 68
        elif beta < 1.3:  risk_base = 55
        elif beta < 1.6:  risk_base = 42
        else:             risk_base = 28
    else:
        risk_base = 60

    debt_eq = r.get("debt_equity") or 0
    debt_penalty = 0 if debt_eq < 1.0 else (5 if debt_eq < 2.0 else 12)
    risk = max(10, risk_base - debt_penalty)

    # Final: Quality 25% + Valuation 25% + Growth 20% + Momentum 15% + Risk 15%
    final_score = int(
        quality   * 0.25 +
        valuation * 0.25 +
        growth    * 0.20 +
        momentum  * 0.15 +
        risk      * 0.15
    )

    return {"quality": quality, "valuation": valuation, "growth": growth,
            "momentum": momentum, "risk": risk, "final_score": final_score}


def _auto_action(upside, score: int) -> str:
    """Derive a recommended action from DCF upside and composite score."""
    if upside is None:
        return "Watch" if score >= 60 else "Hold"
    if score >= 72 and upside > 0.20:  return "Buy"
    if score >= 62 and upside > 0.08:  return "Add"
    if upside > 0.03:                  return "Watch"
    if upside < -0.30:                 return "Avoid"
    return "Hold"


def _auto_risks(ratios: dict, valuation: dict, price: float) -> list:
    """Generate risk flags automatically from financial ratios and valuation output."""
    r = ratios or {}
    v = valuation or {}
    risks = []

    beta = r.get("beta")
    if beta and beta > 1.4:
        risks.append(("High volatility", f"Beta of {beta:.2f} — moves {beta:.1f}× the market. Losses are amplified in downturns.", "warning"))

    debt_eq = r.get("debt_equity")
    if debt_eq and debt_eq > 2.0:
        risks.append(("High leverage", f"Debt/equity of {debt_eq:.1f}× is elevated. Rising rates or a revenue drop could pressure the balance sheet.", "warning"))

    fv = v.get("fair_value_base")
    if fv and price and price > fv * 1.30:
        premium = (price - fv) / fv
        risks.append(("Valuation risk", f"Priced {fmt_pct(premium)} above estimated fair value — limited margin of safety at current levels.", "warning"))

    pe = r.get("pe_ratio")
    if pe and pe > 50:
        risks.append(("High P/E multiple", f"P/E of {pe:.1f}× prices in significant future growth. Any earnings miss could cause multiple compression.", "warning"))

    if v.get("overall_confidence", 100) < 40 and v.get("fair_value_base"):
        risks.append(("Low valuation confidence", f"Valuation confidence is {v.get('overall_confidence', 0):.0f}% — several inputs were estimated.", "info"))

    if not v.get("fair_value_base"):
        risks.append(("Valuation unavailable", "Could not calculate a fair value — insufficient financial data from APIs.", "info"))

    if not risks:
        risks.append(("No major flags detected", "No critical risk flags from available financial data. Always conduct your own research before investing.", "info"))

    return risks


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    _header()
    ticker = _ticker_selector()

    if not ticker:
        _empty_state()
        return

    with st.spinner(f"Loading research for {ticker}…"):
        live_prices = market_data_service.get_watchlist_prices([ticker])
        ratios      = fundamentals_service.get_key_ratios(ticker) or {}
        news        = news_service.get_stock_news(ticker, days_back=14)
        analysts    = news_service.get_analyst_actions(ticker)

    price_data = (live_prices or {}).get(ticker, {})
    price      = price_data.get("price")

    # Run sector-aware valuation (fetches its own financial data and sector info)
    valuation = valuation_engine.run_valuation(ticker, price=price)

    auto_scores     = _calculate_scores(ratios, valuation, price)
    auto_risk_flags = _auto_risks(ratios, valuation, price)

    wl         = _WL_BY_TICKER.get(ticker)
    has_profile = ticker in _PROFILES
    profile    = _PROFILES.get(ticker, _DEFAULT_PROFILE)

    if wl:
        # Watchlist stock — overlay live price, keep manually-researched scores
        wl = wl.copy()
        if price:
            wl["price"] = price
            if wl.get("fair_value"):
                wl["upside_pct"] = (wl["fair_value"] - price) / price
        stock  = wl
        scores = {k: wl[k] for k in ("quality", "valuation", "growth", "momentum", "risk", "final_score")}
        is_auto_scores = False
    else:
        # Any other ticker — build a full stock dict from live data
        fv     = valuation.get("fair_value_base")
        upside = valuation.get("upside_pct") or 0
        action = _auto_action(upside, auto_scores["final_score"])
        stock  = {
            "ticker":    ticker,
            "name":      valuation.get("sector", ticker),
            "sector":    valuation.get("sector", "—"),
            "price":     price or 0,
            "fair_value": fv,
            "buy_below": round(fv * 0.85, 2) if fv else None,
            "upside_pct": upside,
            "action":    action,
        }
        scores         = auto_scores
        is_auto_scores = True

    _stock_header(ticker, stock, profile, is_auto_scores)
    _key_metrics(stock, is_auto_scores)
    if ratios:
        _live_ratios_row(ratios)
    st.markdown("<br>", unsafe_allow_html=True)
    _detail_tabs(ticker, stock, profile, scores, is_auto_scores,
                 valuation, auto_risk_flags, news, analysts, has_profile)


# ── Page sections ─────────────────────────────────────────────────────────────

def _header():
    render_html(
        '<div style="margin-bottom:4px;"><span style="font-size:22px; font-weight:700; '
        'color:#0B0B0F; letter-spacing:-0.02em;">Stock Research</span></div>'
        '<div style="font-size:13px; color:#5B6472;">Deep-dive analysis for any ticker — '
        'valuation, scores, risks, and investment thesis</div>'
    )
    st.markdown('<div style="height:1px; background:#e2e8f0; margin:14px 0 20px;"></div>',
                unsafe_allow_html=True)


def _ticker_selector() -> str:
    # Build a sorted dropdown from all three lists
    _all = sorted(set(
        [h["ticker"] for h in PORTFOLIO_HOLDINGS]
        + [s["ticker"] for s in WATCHLIST]
        + [r["ticker"] for r in RESEARCH_WATCHLIST]
    ))
    col_input, col_select, col_spacer = st.columns([2, 2, 4], gap="small")
    with col_input:
        typed = st.text_input(
            "Enter ticker", placeholder="e.g. MSFT, TSLA, NVDA…",
            label_visibility="collapsed",
        ).upper().strip()
    with col_select:
        options  = ["— Select a stock —"] + _all
        selected = st.selectbox("Or select", options, label_visibility="collapsed")
        if selected != "— Select a stock —":
            return selected
    return typed or ""


def _empty_state():
    render_html(
        '<div style="background:white; border-radius:16px; border:2px dashed #e2e8f0; '
        'padding:60px 40px; text-align:center; margin:40px 0;">'
        '<div style="font-size:48px; margin-bottom:16px;">🔍</div>'
        '<div style="font-size:20px; font-weight:700; color:#374151; margin-bottom:8px;">'
        'Enter any ticker to begin</div>'
        '<div style="font-size:14px; color:#9ca3af; max-width:380px; margin:0 auto;">'
        'Type any stock ticker above — watchlist stocks show manually-researched data, '
        'all others get auto-calculated fair values and scores from live financial data.'
        '</div></div>'
    )


def _stock_header(ticker: str, stock: dict, profile: dict, is_auto: bool):
    action      = stock.get("action", "Watch")
    thesis      = profile.get("thesis_status", "—")
    badge       = html_badge(action, action.lower())
    thesis_var  = thesis.lower() if thesis in ("Intact", "Weakening", "Broken") else "hold"
    thesis_badge = html_badge(thesis, thesis_var) if thesis != "—" else ""
    div_yield   = profile.get("dividend_yield")
    div_html    = (f'<span style="font-size:13px; color:#5B6472; margin-left:8px;">Yield: {div_yield}</span>'
                   if div_yield else "")
    source_badge = html_badge("Auto-calculated", "watch") if is_auto else html_badge("Researched", "buy")
    full_name   = profile.get("full_name") or stock.get("name", ticker)

    render_html(
        f'<div style="background:white; border-radius:12px; border:1px solid #e2e8f0; '
        f'padding:20px 24px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
        f'<div style="display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:10px;">'
        f'<div>'
        f'<div style="font-size:26px; font-weight:800; color:#0B0B0F; letter-spacing:-0.03em; line-height:1.1;">{ticker}</div>'
        f'<div style="font-size:15px; color:#374151; margin-top:3px; font-weight:500;">{full_name}</div>'
        f'<div style="font-size:13px; color:#5B6472; margin-top:2px;">{stock.get("sector", "—")}{div_html}</div>'
        f'</div>'
        f'<div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px;">'
        f'<div style="display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end;">'
        f'{badge}{thesis_badge}{source_badge}</div>'
        f'<div style="font-size:11px; color:#94a3b8;">Updated {now_str()}</div>'
        f'</div></div></div>'
    )


def _key_metrics(stock: dict, is_auto: bool):
    price   = stock.get("price", 0)
    fv      = stock.get("fair_value")
    bb      = stock.get("buy_below")
    upside  = stock.get("upside_pct", 0)
    score   = stock.get("final_score", 50)
    upside_up = upside >= 0

    fv_label = "Fair Value (DCF)" if is_auto else "Fair Value (Base)"
    bb_label = "Buy Below (−15% MoS)" if is_auto else "Buy Below Price"
    fv_delta = "auto from live financials" if is_auto else "weighted estimate"
    bb_delta = "15% margin of safety" if is_auto else "with margin of safety"

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1:
        render_metric_card(label="Current Price", value=fmt_currency(price), icon="💲", accent=True)
    with c2:
        render_metric_card(
            label=fv_label, value=fmt_currency(fv) if fv else "—",
            delta=fv_delta, delta_type="neutral", icon="⚖️",
        )
    with c3:
        render_metric_card(
            label=bb_label, value=fmt_currency(bb) if bb else "—",
            delta=bb_delta, delta_type="neutral", icon="🎯",
        )
    with c4:
        render_metric_card(
            label="Upside / Downside", value=fmt_pct(upside),
            delta="to fair value", delta_type="positive" if upside_up else "negative",
            icon="📈" if upside_up else "📉",
        )
    with c5:
        render_metric_card(
            label="Final Score", value=f"{score}/100",
            delta="investment score",
            delta_type="positive" if score >= 70 else ("neutral" if score >= 50 else "negative"),
            icon="🏆",
        )


def _live_ratios_row(ratios: dict):
    render_section_header("Live Market Ratios", f"Source: {ratios.get('source', 'API')} · {now_str()}", "📡")

    def _fmt(val, pct=False, x=False):
        if val is None: return "—"
        if pct: return fmt_pct(val)
        if x:   return f"{val:.1f}×"
        return f"{val:.2f}"

    c1, c2, c3, c4, c5, c6 = st.columns(6, gap="small")
    with c1: render_metric_card(label="P/E Ratio",      value=_fmt(ratios.get("pe_ratio"),  x=True),  delta_type="neutral", icon="📊")
    with c2: render_metric_card(label="EV/EBITDA",      value=_fmt(ratios.get("ev_ebitda"), x=True),  delta_type="neutral", icon="💹")
    with c3: render_metric_card(label="P/S Ratio",      value=_fmt(ratios.get("ps_ratio"),  x=True),  delta_type="neutral", icon="📈")
    with c4: render_metric_card(label="ROE",            value=_fmt(ratios.get("roe"),       pct=True), delta_type="neutral", icon="🔄")
    with c5: render_metric_card(label="Beta",           value=_fmt(ratios.get("beta")),                delta_type="neutral", icon="⚡")
    with c6:
        div = ratios.get("dividend_yield")
        render_metric_card(label="Dividend Yield", value=_fmt(div, pct=True) if div else "None", delta_type="neutral", icon="💵")
    st.markdown("<br>", unsafe_allow_html=True)


def _detail_tabs(ticker, stock, profile, scores, is_auto_scores,
                 valuation, auto_risk_flags, news, analysts, has_profile):
    tab_overview, tab_val, tab_scores, tab_risks, tab_thesis = st.tabs([
        "📋  Overview", "💰  Valuation", "📊  Scores", "⚠️  Risks", "✅  Thesis",
    ])
    with tab_overview: _tab_overview(ticker, stock, profile, news, analysts, has_profile)
    with tab_val:      _tab_valuation(stock, profile, valuation, is_auto_scores)
    with tab_scores:   _tab_scores(scores, is_auto_scores)
    with tab_risks:    _tab_risks(profile, auto_risk_flags, has_profile)
    with tab_thesis:   _tab_thesis(stock, profile, has_profile)


# ── Tab content ───────────────────────────────────────────────────────────────

def _tab_overview(ticker, stock, profile, news, analysts, has_profile):
    st.markdown("<br>", unsafe_allow_html=True)
    col_desc, col_action = st.columns([3, 2], gap="large")

    with col_desc:
        desc = profile.get("description")
        if desc:
            render_section_header("Company Description", "", "🏢")
            st.markdown(
                f'<p style="font-size:14px; color:#374151; line-height:1.65; margin-top:4px;">{desc}</p>',
                unsafe_allow_html=True,
            )
            models = profile.get("models_used", [])
            if models:
                st.markdown("<br>", unsafe_allow_html=True)
                render_section_header("Valuation Models Used", "", "🔢")
                for m in models:
                    st.markdown(f'<div style="font-size:13px; color:#374151; padding:4px 0;">· {m}</div>',
                                unsafe_allow_html=True)
        else:
            render_section_header("Recent News", f"Last 14 days · {len(news)} articles found", "📰")
            if news:
                for art in news[:6]:
                    headline = art.get("headline", "No headline")
                    source   = art.get("source") or art.get("provider") or ""
                    raw_date = (art.get("published_at") or "")[:10]
                    url      = art.get("url") or ""
                    link     = f'<a href="{url}" target="_blank" style="color:#2563eb; text-decoration:none;">{headline}</a>' if url else headline
                    st.markdown(
                        f'<div style="padding:8px 0; border-bottom:1px solid #f1f5f9;">'
                        f'<div style="font-size:13px; color:#0B0B0F; line-height:1.4;">{link}</div>'
                        f'<div style="font-size:11px; color:#9ca3af; margin-top:2px;">{source} · {raw_date}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No recent news found for this ticker.")

    with col_action:
        render_section_header("Investment Decision", "", "📋")
        action     = stock.get("action", "Watch")
        badge      = html_badge(action, action.lower())
        action_reasons = {
            "Buy":    "Stock is below buy-below price with a strong score. Full position sizing applies.",
            "Add":    "Stock is below fair value and below target weight. Add to existing position.",
            "Hold":   "Stock is near fair value. No action — monitor for a better entry.",
            "Watch":  "High quality stock above buy-below price. Wait for a pullback to buy range.",
            "Trim":   "Position is above target weight or stock is above fair value. Reduce position.",
            "Sell":   "Thesis is deteriorating or stock significantly overvalued. Exit position.",
            "Avoid":  "Score below minimum threshold or data quality insufficient. Do not invest.",
        }
        render_html(
            f'<div style="background:#f8fafc; border-radius:10px; border:1px solid #e2e8f0; padding:18px 20px;">'
            f'<div style="font-size:13px; color:#5B6472; margin-bottom:6px;">Recommended Action</div>'
            f'<div style="font-size:22px; font-weight:700; margin-bottom:8px;">{badge}</div>'
            f'<div style="font-size:13px; color:#374151; line-height:1.5;">{action_reasons.get(action, "")}</div>'
            f'</div>'
        )

        st.markdown("<br>", unsafe_allow_html=True)
        render_section_header("Score Summary", "", "📊")
        for label, key in [("Quality", "quality"), ("Valuation", "valuation"), ("Growth", "growth")]:
            render_score_bar(label, stock.get(key, scores_from_stock(stock, key)))

    # Analyst actions (below both columns)
    if analysts:
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_header("Analyst Actions", f"{len(analysts)} recent rating changes", "🏦")
        for a in analysts[:5]:
            action_str = a.get("action", "")
            firm       = a.get("analyst_firm", "Unknown")
            rating     = a.get("rating", "")
            prior      = a.get("rating_prior", "")
            pt         = a.get("price_target")
            date_str   = (a.get("published_at") or "")[:10]
            arrow      = "🟢" if action_str == "Upgrade" else ("🔴" if action_str == "Downgrade" else "⚪")
            pt_str     = f" · PT: {fmt_currency(pt)}" if pt else ""
            prior_str  = f" (was {prior})" if prior else ""
            st.markdown(
                f'<div style="padding:8px 0; border-bottom:1px solid #f1f5f9; font-size:13px; color:#374151;">'
                f'{arrow} <strong>{firm}</strong> — {action_str} to {rating}{prior_str}{pt_str}'
                f'<span style="color:#9ca3af; float:right;">{date_str}</span></div>',
                unsafe_allow_html=True,
            )

    # Recent news for profile stocks (below the two-column layout)
    if has_profile and news:
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_header("Recent News", f"Last 14 days · {len(news)} articles", "📰")
        for art in news[:5]:
            headline = art.get("headline", "")
            source   = art.get("source") or art.get("provider") or ""
            raw_date = (art.get("published_at") or "")[:10]
            url      = art.get("url") or ""
            link     = f'<a href="{url}" target="_blank" style="color:#2563eb; text-decoration:none;">{headline}</a>' if url else headline
            st.markdown(
                f'<div style="padding:8px 0; border-bottom:1px solid #f1f5f9;">'
                f'<div style="font-size:13px; color:#0B0B0F; line-height:1.4;">{link}</div>'
                f'<div style="font-size:11px; color:#9ca3af; margin-top:2px;">{source} · {raw_date}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def scores_from_stock(stock, key):
    return stock.get(key, 50)


def _tab_valuation(stock, profile, valuation, is_auto):
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Sector classification and model explanation ───────────────────────────
    bucket_label = valuation.get("bucket_label", "General")
    why          = valuation.get("why_these_models", "")
    rating       = valuation.get("valuation_rating", "")
    confidence   = valuation.get("overall_confidence", 0)
    sector       = valuation.get("sector", "Unknown")
    industry     = valuation.get("industry", "")

    rating_colour = {
        "Undervalued":          "#10b981",
        "Slightly Undervalued": "#34d399",
        "Fairly Valued":        "#f59e0b",
        "Slightly Overvalued":  "#f97316",
        "Overvalued":           "#ef4444",
        "Insufficient data":    "#9ca3af",
    }.get(rating, "#9ca3af")

    render_html(
        f'<div style="background:#f0f9ff; border:1px solid #bae6fd; border-radius:10px; padding:16px 20px; margin-bottom:20px;">'
        f'<div style="font-size:12px; font-weight:600; color:#0369a1; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">'
        f'Classified as: {bucket_label} · {sector}{(" — " + industry) if industry and industry != "Unknown" else ""}</div>'
        f'<div style="font-size:13px; color:#374151; line-height:1.6;">{why}</div>'
        f'</div>'
    )

    # ── Blended fair value summary ────────────────────────────────────────────
    fv_low  = valuation.get("fair_value_low")
    fv_base = valuation.get("fair_value_base")
    fv_high = valuation.get("fair_value_high")
    upside  = valuation.get("upside_pct")
    price   = stock.get("price", 0)

    if fv_base:
        render_section_header("Blended Fair Value", f"Weighted average of all successful models · confidence {confidence:.0f}%", "⚖️")
        c1, c2, c3, c4, c5 = st.columns(5, gap="small")
        with c1:
            render_metric_card(label="Low Estimate",  value=fmt_currency(fv_low)  if fv_low  else "—", delta_type="neutral", icon="🔵")
        with c2:
            render_metric_card(label="Base Estimate", value=fmt_currency(fv_base), delta="weighted average", delta_type="neutral", icon="⚖️", accent=True)
        with c3:
            render_metric_card(label="High Estimate", value=fmt_currency(fv_high) if fv_high else "—", delta_type="neutral", icon="🟢")
        with c4:
            render_metric_card(label="Current Price", value=fmt_currency(price), delta_type="neutral", icon="💲")
        with c5:
            upside_type = "positive" if (upside or 0) >= 0 else "negative"
            render_metric_card(
                label="Upside / Downside", value=fmt_pct(upside or 0),
                delta=rating, delta_type=upside_type, icon="📈" if (upside or 0) >= 0 else "📉",
            )
        st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.warning("No fair value could be calculated — all models failed due to missing financial data.")

    # ── Manual research fair value (watchlist stocks with profiles) ───────────
    fv_range = profile.get("fair_value_range", {})
    if fv_range:
        render_section_header("Research Fair Value Range", "Manually-researched scenario analysis", "🔬")
        cols = st.columns(len(fv_range) + 1, gap="small")
        for col, (label, val) in zip(cols, fv_range.items()):
            is_base = label == "Base"
            with col:
                render_metric_card(
                    label=label + " Case", value=fmt_currency(val),
                    delta="central estimate" if is_base else label.lower() + " scenario",
                    delta_type="neutral",
                    icon="🔵" if is_base else ("🟢" if label == "Optimistic" else "🔴"),
                    accent=is_base,
                )
        fv_base_manual = fv_range.get("Base", price)
        with cols[-1]:
            manual_upside = (fv_base_manual - price) / price if price else 0
            render_metric_card(
                label="Current Price", value=fmt_currency(price),
                delta=fmt_pct(manual_upside) + " to base",
                delta_type="positive" if manual_upside >= 0 else "negative", icon="💲",
            )
        assumptions = profile.get("key_assumptions", {})
        if assumptions:
            st.markdown("<br>", unsafe_allow_html=True)
            render_section_header("Key Assumptions", "Inputs driving the research model", "⚙️")
            cols2 = st.columns(len(assumptions), gap="small")
            for col, (k, v) in zip(cols2, assumptions.items()):
                with col:
                    render_metric_card(label=k, value=v, delta_type="neutral")
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Individual model results ──────────────────────────────────────────────
    models_run = valuation.get("models_run", {})
    if models_run:
        render_section_header("Individual Model Results", "Each model's fair value estimate and confidence", "🔢")
        weights_used = valuation.get("weights_used", {})

        for model_key, result in models_run.items():
            fv       = result.get("fair_value")
            conf     = result.get("confidence", 0)
            name     = result.get("name", model_key)
            weight   = weights_used.get(model_key, 0)
            inp      = result.get("inputs_used", {})
            warns    = result.get("warnings", [])
            status   = "✅" if fv else "❌"
            fv_str   = fmt_currency(fv) if fv else "Failed"

            # Build a compact key inputs string
            inp_parts = []
            for k, v in list(inp.items())[:3]:
                label = k.replace("_", " ").title()
                val_str = fmt_currency(v) if isinstance(v, float) and v > 100 else (
                    fmt_pct(v) if isinstance(v, float) and 0 < v < 10 else str(v)
                )
                inp_parts.append(f"{label}: {val_str}")
            inp_str = " · ".join(inp_parts) if inp_parts else "—"

            inp_html  = (f'<div style="font-size:12px; color:#5B6472; margin-top:6px;">{inp_str}</div>'
                         if inp_str and inp_str != "—" else "")
            warn_html = "".join(
                f'<div style="font-size:11px; color:#9ca3af; margin-top:3px;">⚠️ {w}</div>'
                for w in warns[:1]
            )
            bg_col  = "#f0fdf4" if fv else "#fef2f2"
            brd_col = "#86efac" if fv else "#fca5a5"
            fv_col  = "#166534" if fv else "#991b1b"
            render_html(
                f'<div style="background:{bg_col}; border:1px solid {brd_col}; '
                f'border-radius:10px; padding:14px 18px; margin-bottom:10px;">'
                f'<div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">'
                f'<span style="font-size:15px;">{status}</span>'
                f'<span style="font-size:14px; font-weight:700; color:#0B0B0F; min-width:220px;">{name}</span>'
                f'<span style="font-size:16px; font-weight:800; color:{fv_col};">{fv_str}</span>'
                f'<span style="font-size:12px; color:#5B6472; margin-left:auto;">Weight: {weight:.0%} · Confidence: {conf:.0f}%</span>'
                f'</div>'
                f'{inp_html}{warn_html}'
                f'</div>'
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(
        "All fair values are estimates. Sector benchmark multiples are long-run averages and may not reflect "
        "current market conditions. Always verify with your own research before investing."
    )


def _tab_scores(scores: dict, is_auto: bool):
    st.markdown("<br>", unsafe_allow_html=True)

    score_meta = {
        "quality":   ("Quality",   "ROIC, ROE — measures business quality and capital efficiency"),
        "valuation": ("Valuation", "Upside to fair value — how attractive the price is vs intrinsic value"),
        "growth":    ("Growth",    "Revenue growth YoY — pace of business expansion"),
        "momentum":  ("Momentum",  "Position in 52-week range — contrarian entry signal"),
        "risk":      ("Risk",      "Beta and leverage — stability and downside protection"),
    }

    col_bars, col_explain = st.columns([2, 3], gap="large")

    with col_bars:
        label = "Auto-Calculated Scores" if is_auto else "Research Scores"
        render_section_header(label, "0 = weak · 100 = exceptional", "📊")
        for key, (name, _) in score_meta.items():
            render_score_bar(name, scores.get(key, 50))
        st.markdown("<br>", unsafe_allow_html=True)
        render_score_bar("Final Score (weighted)", scores.get("final_score", 50))

    with col_explain:
        render_section_header("What each score measures", "", "📖")
        for key, (name, desc) in score_meta.items():
            score     = scores.get(key, 50)
            band      = "Strong" if score >= 70 else ("Average" if score >= 50 else "Weak")
            band_var  = "buy" if score >= 70 else ("watch" if score >= 50 else "sell")
            badge     = html_badge(band, band_var)
            render_html(
                f'<div style="padding:10px 14px; background:#f8fafc; border-radius:9px; '
                f'border:1px solid #f1f5f9; margin-bottom:8px;">'
                f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:3px;">'
                f'<span style="font-size:13px; font-weight:600; color:#0B0B0F;">{name}</span>{badge}'
                f'<span style="font-size:12px; color:#9ca3af; margin-left:auto;">{score}/100</span></div>'
                f'<div style="font-size:12px; color:#5B6472;">{desc}</div></div>'
            )

    st.markdown("<br>", unsafe_allow_html=True)
    if is_auto:
        st.caption(
            "⚙️ Scores are auto-calculated from live financial data (ROIC, ROE, revenue growth, beta, DCF upside). "
            "They are approximate — manually-researched scores on watchlist stocks are more accurate."
        )
    else:
        st.caption(
            "Final Score = Quality×25% + Valuation×25% + Growth×20% + Momentum×15% + Risk×15%."
        )


def _tab_risks(profile: dict, auto_risk_flags: list, has_profile: bool):
    st.markdown("<br>", unsafe_allow_html=True)
    risks = profile.get("risks", []) if has_profile else []

    level_icon   = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}
    level_bg     = {"critical": "#fef2f2", "warning": "#fffbeb", "info": "#eff6ff"}
    level_border = {"critical": "#fca5a5", "warning": "#fde68a", "info": "#bfdbfe"}
    level_text   = {"critical": "#991b1b",  "warning": "#854d0e", "info": "#1e40af"}

    def _risk_card(name, description, level):
        icon   = level_icon.get(level, "⚠️")
        bg     = level_bg.get(level, "#fffbeb")
        border = level_border.get(level, "#fde68a")
        colour = level_text.get(level, "#854d0e")
        badge  = html_badge(level.capitalize(), level)
        render_html(
            f'<div style="background:{bg}; border:1px solid {border}; border-radius:10px; '
            f'padding:14px 18px; margin-bottom:10px;">'
            f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">'
            f'<span style="font-size:15px;">{icon}</span>'
            f'<span style="font-size:14px; font-weight:600; color:{colour};">{name}</span>'
            f'<span style="margin-left:auto;">{badge}</span></div>'
            f'<div style="font-size:13px; color:#374151;">{description}</div></div>'
        )

    if risks:
        critical = sum(1 for r in risks if r[2] == "critical")
        warnings = sum(1 for r in risks if r[2] == "warning")
        render_section_header(
            "Key Risk Factors",
            f"{critical} critical · {warnings} warnings · {len(risks) - critical - warnings} low",
            "⚠️",
        )
        for name, description, level in risks:
            _risk_card(name, description, level)
    else:
        render_section_header("Auto-Generated Risk Flags", "Derived from live financial ratios", "⚠️")
        for name, description, level in auto_risk_flags:
            _risk_card(name, description, level)
        st.caption(
            "⚙️ Risk flags are auto-generated from live data (beta, debt/equity, P/E, DCF upside). "
            "Add this stock to your watchlist and write a research note for hand-crafted risk analysis."
        )


def _tab_thesis(stock: dict, profile: dict, has_profile: bool):
    st.markdown("<br>", unsafe_allow_html=True)
    thesis_items = profile.get("thesis", []) if has_profile else []
    status       = profile.get("thesis_status", "—") if has_profile else "—"

    col_thesis, col_status = st.columns([3, 2], gap="large")

    with col_thesis:
        render_section_header("Investment Thesis", "Key reasons to own this stock", "✅")
        if thesis_items:
            for point, passes in thesis_items:
                icon   = "✅" if passes else "⚠️"
                colour = "#14532d" if passes else "#92400e"
                bg     = "#f0fdf4" if passes else "#fefce8"
                border = "#86efac" if passes else "#fde047"
                render_html(
                    f'<div style="background:{bg}; border:1px solid {border}; border-radius:8px; '
                    f'padding:10px 14px; margin-bottom:7px; display:flex; align-items:center; gap:10px;">'
                    f'<span style="font-size:15px;">{icon}</span>'
                    f'<span style="font-size:13px; color:{colour}; line-height:1.4;">{point}</span></div>'
                )
        else:
            render_html(
                '<div style="background:#f8fafc; border:2px dashed #e2e8f0; border-radius:10px; '
                'padding:30px 24px; text-align:center;">'
                '<div style="font-size:24px; margin-bottom:10px;">📝</div>'
                '<div style="font-size:14px; font-weight:600; color:#374151; margin-bottom:6px;">'
                'No thesis written for this stock</div>'
                '<div style="font-size:13px; color:#9ca3af;">Add this ticker to your watchlist and '
                'write a research note to track your investment thesis here.</div></div>'
            )

    with col_status:
        render_section_header("Thesis Status", "", "📋")
        if status != "—":
            status_var   = status.lower() if status in ("Intact", "Weakening", "Broken") else "hold"
            status_badge = html_badge(status, status_var)
            status_desc  = {
                "Intact":    "All key thesis pillars are holding. Continue to hold or add at the right price.",
                "Weakening": "One or more thesis pillars are under pressure. Monitor closely before adding.",
                "Broken":    "Core thesis no longer holds. Consider exiting the position.",
            }.get(status, "")
            render_html(
                f'<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; '
                f'padding:20px; text-align:center;">'
                f'<div style="font-size:13px; color:#5B6472; margin-bottom:8px;">Current Status</div>'
                f'<div style="font-size:20px; margin-bottom:12px;">{status_badge}</div>'
                f'<div style="font-size:13px; color:#374151; line-height:1.5;">{status_desc}</div></div>'
            )
        else:
            st.info("Thesis status not assessed — only available for manually-researched watchlist stocks.")
