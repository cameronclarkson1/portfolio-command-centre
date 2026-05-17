"""
intelligence.py — Market Intelligence Hub (Stage 4 redesign).

Layout:
  1. Header with summary counts
  2. News summary metric tiles (from AI-analysed items)
  3. Live Headlines — fetch real headlines from news_service for any watchlist ticker
  4. AI Analyst Feed — expandable cards with manually-written analysis
  5. Disclaimer
"""

import streamlit as st
from datetime import datetime

from components import (
    render_section_header,
    render_metric_card,
    html_badge,
    render_html,
    now_str,
)
from utils.sample_data import NEWS_ITEMS, PORTFOLIO_HOLDINGS, WATCHLIST, RESEARCH_WATCHLIST
from services import news_service

_SENTIMENT_CONFIG = {
    "Positive": ("#f0fdf4", "#86efac", "#166534", "✅"),
    "Negative": ("#fef2f2", "#fca5a5", "#991b1b", "❌"),
    "Neutral":  ("#f8fafc", "#e2e8f0", "#374151", "⚪"),
    "Mixed":    ("#fefce8", "#fde047", "#854d0e", "⚠️"),
}

_THESIS_CONFIG = {
    "Intact":    ("#f0fdf4", "#166534", "intact"),
    "Weakening": ("#fefce8", "#854d0e", "weakening"),
    "Broken":    ("#fef2f2", "#991b1b", "broken"),
}


def render():
    _header()
    _summary_metrics()
    st.markdown("<br>", unsafe_allow_html=True)
    _live_headlines()
    st.markdown("<br>", unsafe_allow_html=True)
    _filter_bar()
    st.markdown("<br>", unsafe_allow_html=True)
    _news_feed()
    _disclaimer()


# ── Sections ──────────────────────────────────────────────────────────────────

def _header():
    render_html(
        f'<div style="margin-bottom:4px;"><span style="font-size:22px; font-weight:700; color:#0B0B0F; letter-spacing:-0.02em;">Intelligence Hub</span></div>'
        f'<div style="font-size:13px; color:#5B6472;">Live headlines + AI analyst impact summaries · {datetime.now().strftime("%d %B %Y")}</div>'
    )
    st.markdown('<div style="height:1px; background:#e2e8f0; margin:14px 0 20px;"></div>', unsafe_allow_html=True)


def _summary_metrics():
    total     = len(NEWS_ITEMS)
    positive  = sum(1 for n in NEWS_ITEMS if n["sentiment"] == "Positive")
    negative  = sum(1 for n in NEWS_ITEMS if n["sentiment"] == "Negative")
    intact    = sum(1 for n in NEWS_ITEMS if n["thesis"] == "Intact")
    weakening = sum(1 for n in NEWS_ITEMS if n["thesis"] == "Weakening")

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1:
        render_metric_card(
            label="AI Analyses", value=str(total),
            delta="in analyst feed", delta_type="neutral", icon="🤖", accent=True,
        )
    with c2:
        render_metric_card(
            label="Positive", value=str(positive),
            delta="bullish impact", delta_type="positive", icon="✅",
        )
    with c3:
        render_metric_card(
            label="Negative", value=str(negative),
            delta="bearish impact", delta_type="negative", icon="❌",
        )
    with c4:
        render_metric_card(
            label="Thesis Intact", value=str(intact),
            delta="holding", delta_type="positive", icon="🛡️",
        )
    with c5:
        render_metric_card(
            label="Thesis Weakening", value=str(weakening),
            delta="monitor closely", delta_type="warning" if weakening > 0 else "neutral",
            icon="⚠️",
        )


def _live_headlines():
    """Fetch and display live news headlines for any watchlist ticker."""
    render_section_header(
        "Live Headlines",
        "Real-time news from your watchlist — select a stock to load latest articles",
        "📡",
    )

    # Include portfolio, watchlist, and research stocks in the ticker picker
    _all_stocks = (
        {h["ticker"]: h["name"] for h in PORTFOLIO_HOLDINGS}
        | {s["ticker"]: s["name"] for s in WATCHLIST}
        | {r["ticker"]: r["name"] for r in RESEARCH_WATCHLIST}
    )
    tickers = [f"{t} — {n}" for t, n in sorted(_all_stocks.items())]
    col_pick, col_days, _ = st.columns([2, 1, 3], gap="small")

    with col_pick:
        choice = st.selectbox("Stock", tickers, label_visibility="collapsed", key="intel_live_ticker")
    with col_days:
        days = st.selectbox("Period", ["7 days", "14 days", "30 days"],
                            label_visibility="collapsed", key="intel_live_days")

    ticker   = choice.split(" — ")[0]
    days_int = int(days.split()[0])

    with st.spinner(f"Fetching latest news for {ticker}…"):
        articles = news_service.get_stock_news(ticker, days_back=days_int)

    if not articles:
        st.warning(f"No live headlines found for {ticker} — news API may be unavailable or no articles in the last {days_int} days.")
        return

    st.caption(f"{len(articles)} articles found · source: {articles[0].get('provider', 'API')}")

    for art in articles[:15]:  # cap at 15 so the page doesn't get too long
        _live_news_card(art)


def _live_news_card(art: dict):
    """Simple card for a live headline (no AI analysis fields)."""
    headline = art.get("headline") or "No headline"
    source   = art.get("source") or art.get("provider") or "Unknown"
    raw_date = art.get("published_at") or ""
    summary  = art.get("summary") or ""
    url      = art.get("url") or ""

    # Try to format the date neatly
    date_str = raw_date
    if raw_date and "T" in raw_date:
        try:
            date_str = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).strftime("%d %b %Y %H:%M")
        except Exception:
            date_str = raw_date[:10]

    label = f"📰 {headline}"
    with st.expander(label, expanded=False):
        st.markdown(
            f'<div style="font-size:12px; color:#9ca3af; margin-bottom:8px;">'
            f'{source} · {date_str}</div>',
            unsafe_allow_html=True,
        )
        if summary:
            st.markdown(
                f'<div style="font-size:13px; color:#374151; line-height:1.65;">{summary[:500]}{"…" if len(summary) > 500 else ""}</div>',
                unsafe_allow_html=True,
            )
        if url:
            st.markdown(f"[Read full article →]({url})")


def _filter_bar():
    render_section_header("AI Analyst Feed", "Manually-researched summaries — click any item to expand", "🧠")

    f1, f2, f3, f4 = st.columns([2, 2, 2, 2], gap="small")

    with f1:
        tickers = ["All Stocks"] + sorted({n["ticker"] for n in NEWS_ITEMS})
        st.selectbox("Stock", tickers, label_visibility="collapsed", key="intel_ticker")
    with f2:
        st.selectbox(
            "Sentiment", ["All Sentiments", "Positive", "Negative", "Neutral", "Mixed"],
            label_visibility="collapsed", key="intel_sentiment",
        )
    with f3:
        st.selectbox(
            "Thesis Status", ["All Status", "Intact", "Weakening", "Broken"],
            label_visibility="collapsed", key="intel_thesis",
        )
    with f4:
        st.selectbox(
            "Sort by", ["Newest first", "Ticker A–Z", "Positive first", "Negative first"],
            label_visibility="collapsed", key="intel_sort",
        )


def _news_feed():
    items = NEWS_ITEMS.copy()

    ticker_f    = st.session_state.get("intel_ticker",    "All Stocks")
    sentiment_f = st.session_state.get("intel_sentiment", "All Sentiments")
    thesis_f    = st.session_state.get("intel_thesis",    "All Status")
    sort_f      = st.session_state.get("intel_sort",      "Newest first")

    if ticker_f    != "All Stocks":
        items = [n for n in items if n["ticker"] == ticker_f]
    if sentiment_f != "All Sentiments":
        items = [n for n in items if n["sentiment"] == sentiment_f]
    if thesis_f    != "All Status":
        items = [n for n in items if n["thesis"] == thesis_f]

    if sort_f == "Ticker A–Z":
        items.sort(key=lambda n: n["ticker"])
    elif sort_f == "Positive first":
        order = {"Positive": 0, "Mixed": 1, "Neutral": 2, "Negative": 3}
        items.sort(key=lambda n: order.get(n["sentiment"], 9))
    elif sort_f == "Negative first":
        order = {"Negative": 0, "Mixed": 1, "Neutral": 2, "Positive": 3}
        items.sort(key=lambda n: order.get(n["sentiment"], 9))

    if not items:
        st.info("No news items match the current filters.")
        return

    for item in items:
        _news_card(item)


def _news_card(item: dict):
    """Expandable news card with AI summary and impact/thesis badges."""
    sent_bg, sent_border, sent_text, sent_icon = _SENTIMENT_CONFIG.get(
        item["sentiment"], _SENTIMENT_CONFIG["Neutral"]
    )
    thesis_bg, thesis_text, thesis_var = _THESIS_CONFIG.get(
        item["thesis"], ("#f8fafc", "#374151", "hold")
    )

    tags_html = " ".join(
        f'<span style="background:#f1f5f9; color:#475569; padding:2px 9px; '
        f'border-radius:10px; font-size:11px; font-weight:500;">{t}</span>'
        for t in item.get("tags", [])
    )

    sentiment_badge = html_badge(item["sentiment"], item["sentiment"].lower())
    thesis_badge    = html_badge(item["thesis"],    thesis_var)
    impact_badge    = html_badge(item["impact"],    item["impact"].lower())

    label = f"{sent_icon} **{item['ticker']}** — {item['headline']}"

    with st.expander(label, expanded=False):
        st.markdown("<br>", unsafe_allow_html=True)

        col_main, col_meta = st.columns([3, 1], gap="large")

        with col_main:
            st.markdown(
                f'<div style="font-size:12px; color:#9ca3af; margin-bottom:8px;">'
                f'{item["source"]} · {item["date"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(tags_html + "<br>", unsafe_allow_html=True)

            render_html(
                f'<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:16px 18px; margin-top:8px;">'
                f'<div style="font-size:12px; font-weight:600; color:#5B6472; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;">🤖 AI Analyst Summary</div>'
                f'<div style="font-size:13px; color:#374151; line-height:1.65;">{item["summary"]}</div>'
                f'</div>'
            )

        with col_meta:
            render_html(
                f'<div style="background:white; border:1px solid #e2e8f0; border-radius:10px; padding:16px; text-align:center; height:100%;">'
                f'<div style="font-size:10px; color:#9ca3af; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:5px;">Sentiment</div>'
                f'<div style="margin-bottom:12px;">{sentiment_badge}</div>'
                f'<div style="height:1px; background:#f1f5f9; margin:10px 0;"></div>'
                f'<div style="font-size:10px; color:#9ca3af; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:5px;">Market Impact</div>'
                f'<div style="margin-bottom:12px;">{impact_badge}</div>'
                f'<div style="height:1px; background:#f1f5f9; margin:10px 0;"></div>'
                f'<div style="font-size:10px; color:#9ca3af; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:5px;">Thesis Status</div>'
                f'<div>{thesis_badge}</div>'
                f'</div>'
            )

        st.markdown("<br>", unsafe_allow_html=True)


def _disclaimer():
    st.divider()
    st.caption(
        "⚠️ **Disclaimer:** AI summaries in the Analyst Feed are manually-written decision-support analysis — not financial advice. "
        "Live Headlines are fetched directly from news APIs and are not AI-analysed. "
        "Always verify headlines from primary sources before acting."
    )
