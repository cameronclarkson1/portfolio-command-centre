"""
news_service.py — News headlines and analyst actions for the Intelligence Hub.

Functions:
  get_stock_news(ticker, days_back)  → news articles for a specific ticker
  get_analyst_actions(ticker)        → analyst rating changes
  get_earnings_events(ticker)        → upcoming earnings dates and estimates

Fallback order for stock news:    Finnhub company news → FMP stock news
Fallback order for analyst data:  FMP historical-grade (no other free source)
Fallback order for earnings:      Finnhub earnings calendar
"""

import providers.finnhub_provider as finnhub
import providers.fmp_provider     as fmp

from services import _try_providers
from storage.cache_manager import cache
from config.settings import CACHE_TTL
from utils.logging_utils import get_logger, log_cache_hit, log_cache_miss

log = get_logger(__name__)


def get_stock_news(ticker: str, days_back: int = 7) -> list[dict]:
    """
    Return recent news articles for a ticker.

    Each item:
    {
        "headline":     "Alphabet Reports Strong Q1 ...",
        "summary":      "...",
        "source":       "Reuters",
        "url":          "https://...",
        "published_at": "2026-05-13T10:00:00Z",
        "ticker":       "GOOGL",
        "provider":     "finnhub",
    }

    Fallback: Finnhub company news → FMP stock news
    """
    ticker    = ticker.upper()
    cache_key = f"news:{ticker}:{days_back}d"
    ttl       = CACHE_TTL["news"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    result, source, _ = _try_providers([
        ("finnhub", lambda: finnhub.get_company_news(ticker, days_back=days_back)),
        ("fmp",     lambda: fmp.get_stock_news(ticker)),
    ], f"{ticker} news")

    articles = result or []

    # Standardise all articles to the same shape regardless of provider
    clean = []
    for item in articles:
        clean.append({
            "headline":     item.get("headline") or item.get("title"),
            "summary":      item.get("summary")  or item.get("body") or "",
            "source":       item.get("source")   or item.get("author") or source,
            "url":          item.get("url") or "",
            "published_at": item.get("published_at"),
            "ticker":       ticker,
            "provider":     item.get("provider") or source,
        })

    if clean:
        cache.set(cache_key, clean, ttl)

    return clean


def get_analyst_actions(ticker: str) -> list[dict]:
    """
    Return recent analyst rating changes (upgrades, downgrades, new coverage).

    Each item:
    {
        "ticker":             "MSFT",
        "analyst_firm":       "Goldman Sachs",
        "action":             "Upgrade",
        "rating":             "Buy",
        "rating_prior":       "Neutral",
        "price_target":       None,       # not available from FMP grades endpoint
        "price_target_prior": None,
        "published_at":       "2026-05-10",
        "bucket":             "buy",      # buy | hold | sell
        "provider":           "fmp",
    }

    Source: FMP /historical-grade endpoint.
    """
    ticker    = ticker.upper()
    cache_key = f"analyst:{ticker}"
    ttl       = CACHE_TTL["analyst_actions"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    result, _, _ = _try_providers([
        ("fmp", lambda: fmp.get_analyst_grades(ticker)),
    ], f"{ticker} analyst ratings")

    actions = result or []

    if actions:
        cache.set(cache_key, actions, ttl)

    return actions


def get_earnings_events(ticker: str) -> list[dict]:
    """
    Return upcoming earnings dates and estimates for a ticker.

    Each item:
    {
        "ticker":       "AAPL",
        "date":         "2026-07-30",
        "hour":         "amc",      # amc = after market close, bmo = before market open
        "eps_estimate": 1.42,
        "revenue_est":  95000000000,
        "provider":     "finnhub",
    }

    Source: Finnhub earnings calendar.
    """
    ticker    = ticker.upper()
    cache_key = f"earnings:{ticker}"
    ttl       = CACHE_TTL["earnings_events"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    result, _, _ = _try_providers([
        ("finnhub", lambda: finnhub.get_earnings_calendar(ticker)),
    ], f"{ticker} earnings calendar")

    events = result or []

    if events:
        cache.set(cache_key, events, ttl)

    return events
