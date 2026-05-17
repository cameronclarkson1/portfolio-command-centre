"""
event_detection_service.py — Event classification and risk scoring.

Turns a list of news headlines into classified events with an overall risk score.
Classification uses keyword matching (AI-powered classification comes in Stage 4).

Functions:
  classify_events(news_items)     → news items with event_type tags added
  get_event_risk_score(ticker)    → Low / Medium / High + plain-English reason
  get_event_risk_flags(ticker)    → combines news + earnings + GDELT into one risk view
"""

import providers.gdelt_provider   as gdelt
from services.news_service import get_stock_news, get_earnings_events
from storage.cache_manager import cache
from config.settings import CACHE_TTL, EVENT_CATEGORIES
from utils.logging_utils import get_logger, log_cache_hit, log_cache_miss

log = get_logger(__name__)

# ── Keyword → event type classification ──────────────────────────────────────
# Each entry: (event_type_label, positive_keywords, negative_keywords)
# A headline is scanned for these keywords to assign an event type.

_EVENT_RULES = [
    ("Earnings",           ["earnings", "quarterly results", "q1", "q2", "q3", "q4", "eps", "revenue beat", "revenue miss"], []),
    ("Guidance Change",    ["guidance", "outlook", "forecast", "raised guidance", "lowered guidance", "cuts forecast"], []),
    ("Analyst Upgrade",    ["upgrade", "upgraded", "raises rating", "upgraded to buy", "upgraded to outperform"], []),
    ("Analyst Downgrade",  ["downgrade", "downgraded", "lowers rating", "downgraded to sell", "downgraded to underperform"], []),
    ("Price Target Change",["price target", "pt raised", "pt lowered", "target raised", "target cut"], []),
    ("SEC Filing",         ["10-k", "10-q", "8-k", "sec filing", "proxy statement", "annual report"], []),
    ("Insider Buying",     ["insider buy", "insider purchase", "director buys", "ceo buys"], []),
    ("Insider Selling",    ["insider sell", "insider sale", "director sells", "ceo sells"], []),
    ("Management Change",  ["ceo", "cfo", "coo", "chief executive", "appointed", "resigned", "departure", "steps down"], []),
    ("Legal / Regulatory", ["lawsuit", "regulatory", "fine", "penalty", "investigation", "antitrust", "sec probe"], []),
    ("M&A Activity",       ["acquisition", "merger", "buyout", "takeover", "acquires", "deal", "joint venture"], []),
    ("Product Launch",     ["launches", "launch", "unveils", "announces new", "new product", "partnership"], []),
    ("Macro Shock",        ["federal reserve", "fed", "interest rate", "inflation", "gdp", "recession", "tariff"], []),
    ("Controversy",        ["controversy", "scandal", "backlash", "criticism", "accused", "alleged", "misconduct"], []),
    ("Geopolitical Risk",  ["geopolitical", "sanctions", "war", "conflict", "trade war", "export ban"], []),
]

# Risk weight for each event type (how much does it raise the risk score?)
_EVENT_RISK_WEIGHTS = {
    "Analyst Downgrade":   3,
    "Legal / Regulatory":  3,
    "Controversy":         3,
    "Geopolitical Risk":   2,
    "Insider Selling":     2,
    "Guidance Change":     2,
    "Management Change":   2,
    "Macro Shock":         1,
    "Earnings":            1,
    "SEC Filing":          0,
    "Analyst Upgrade":    -2,   # upgrades reduce risk score
    "Insider Buying":     -1,
    "Product Launch":     -1,
}


def classify_events(news_items: list[dict]) -> list[dict]:
    """
    Add an 'event_type' field to each news item based on headline keywords.

    Also adds a 'risk_contribution' field (how much this event raises the risk score).

    Args:
        news_items: List of news dicts from news_service.get_stock_news()

    Returns: Same list with 'event_type' and 'risk_contribution' added to each item.
    """
    classified = []
    for item in news_items:
        headline = (item.get("headline") or "").lower()
        summary  = (item.get("summary")  or "").lower()
        text     = headline + " " + summary

        event_type       = "Other"
        risk_contribution = 0

        for label, keywords, _ in _EVENT_RULES:
            if any(kw in text for kw in keywords):
                event_type        = label
                risk_contribution = _EVENT_RISK_WEIGHTS.get(label, 0)
                break

        classified.append({
            **item,
            "event_type":        event_type,
            "risk_contribution": risk_contribution,
        })

    return classified


def get_event_risk_score(ticker: str) -> dict:
    """
    Return an overall event risk score for a ticker based on recent news.

    Combines:
      - News event classification (headline keyword matching)
      - Upcoming earnings proximity (within 30 days = +1 risk)
      - GDELT sentiment tone (if very negative = +1 risk)

    Returns:
    {
        "ticker":     "MSFT",
        "risk_score":  4,           # raw integer score
        "risk_level": "Medium",     # Low | Medium | High
        "reason":     "Recent analyst downgrade and two negative regulatory headlines.",
        "events":     [...],        # classified news items
        "source":     "finnhub+gdelt",
    }
    """
    ticker    = ticker.upper()
    cache_key = f"event_risk:{ticker}"
    ttl       = CACHE_TTL["event_risk"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    # 1. Get and classify recent news
    news_items = get_stock_news(ticker, days_back=14)
    events     = classify_events(news_items)

    # 2. Sum risk contributions from events
    risk_score   = sum(e.get("risk_contribution", 0) for e in events)
    reason_parts = []

    # Summarise which event types are driving the score
    from collections import Counter
    event_counts = Counter(e["event_type"] for e in events if e["event_type"] != "Other")

    for event_type, count in event_counts.most_common(3):
        weight = _EVENT_RISK_WEIGHTS.get(event_type, 0)
        if weight > 0:
            reason_parts.append(f"{count} {event_type.lower()} event{'s' if count > 1 else ''}")
        elif weight < 0:
            reason_parts.append(f"{count} positive {event_type.lower()} event{'s' if count > 1 else ''}")

    # 3. Check for upcoming earnings (adds 1 to risk — uncertainty)
    earnings = get_earnings_events(ticker)
    if earnings:
        risk_score += 1
        reason_parts.append("upcoming earnings date")

    # 4. GDELT sentiment check (supplementary, noisy)
    try:
        from utils.logging_utils import get_logger as _gl
        gdelt_data = gdelt.get_event_tone(ticker)
        if gdelt_data.get("risk_flag"):
            risk_score  += 1
            reason_parts.append("negative global news tone (GDELT)")
    except Exception as e:
        log.debug(f"GDELT tone check skipped: {e}")

    # 5. Convert score to level label
    if risk_score >= 6:
        risk_level = "High"
    elif risk_score >= 3:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    reason = (
        "Recent: " + ", ".join(reason_parts) + "."
        if reason_parts
        else "No significant events detected in the past 14 days."
    )

    result = {
        "ticker":     ticker,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason":     reason,
        "events":     events,
        "earnings":   earnings,
        "source":     "finnhub+gdelt",
    }

    cache.set(cache_key, result, ttl)
    return result


def get_event_risk_flags(ticker: str) -> dict:
    """
    Convenience wrapper — returns get_event_risk_score.
    Named to match the function list in the architecture spec.
    """
    return get_event_risk_score(ticker)
