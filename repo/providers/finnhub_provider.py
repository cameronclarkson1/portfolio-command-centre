"""
finnhub_provider.py — Raw API calls to Finnhub.

Used as: backup price source, company news, insider transactions,
earnings calendar, and financial metric enrichment.

Free tier: 60 API calls/minute.
"""

import requests
from datetime import datetime, timezone, timedelta

from config.api_keys import FINNHUB_API_KEY
from config.settings import FINNHUB_BASE, REQUEST_TIMEOUT
from utils.logging_utils import get_logger, log_provider_call
from utils.date_utils import to_date_str, n_days_ago_str

log = get_logger(__name__)


def _get(endpoint: str, params: dict = None) -> dict | list:
    """
    Make a GET request to Finnhub.
    Raises ValueError if no API key is configured.
    """
    if not FINNHUB_API_KEY:
        raise ValueError("FINNHUB_API_KEY not configured")

    url = f"{FINNHUB_BASE}{endpoint}"
    all_params = {"token": FINNHUB_API_KEY, **(params or {})}

    resp = requests.get(url, params=all_params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_quote(ticker: str) -> dict:
    """
    Get the current price quote for a ticker.

    Finnhub quote fields:
      c  = current price
      d  = change (dollars)
      dp = change percent
      h  = high today
      l  = low today
      o  = open today
      pc = previous close
    """
    log_provider_call(log, "Finnhub", f"/quote?symbol={ticker}", ticker)

    data = _get("/quote", params={"symbol": ticker})

    if not data or data.get("c") is None:
        raise ValueError(f"Finnhub returned no quote for {ticker}")

    change_pct = (data.get("dp") or 0.0) / 100  # convert 1.22 → 0.0122

    return {
        "ticker":     ticker.upper(),
        "price":      data.get("c"),
        "change_pct": change_pct,
        "high":       data.get("h"),
        "low":        data.get("l"),
        "open":       data.get("o"),
        "prev_close": data.get("pc"),
        "source":     "finnhub",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_company_news(ticker: str, days_back: int = 7) -> list[dict]:
    """
    Get recent company news articles from Finnhub.

    Args:
        ticker:    Stock ticker
        days_back: How many days of news to fetch (default 7)

    Returns a list of article dicts with: headline, summary, source, url, published_at
    """
    from_date = n_days_ago_str(days_back)
    to_date   = to_date_str()

    log_provider_call(log, "Finnhub", f"/company-news?symbol={ticker}&from={from_date}", ticker)

    data = _get("/company-news", params={
        "symbol": ticker,
        "from":   from_date,
        "to":     to_date,
    })

    articles = []
    for item in (data or []):
        # Convert Unix timestamp to ISO string
        ts = item.get("datetime", 0)
        published = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None

        articles.append({
            "headline":     item.get("headline"),
            "summary":      item.get("summary"),
            "source":       item.get("source"),
            "url":          item.get("url"),
            "image_url":    item.get("image"),
            "published_at": published,
            "ticker":       ticker.upper(),
            "provider":     "finnhub",
        })

    return articles


def get_market_news(category: str = "general", limit: int = 20) -> list[dict]:
    """
    Get general market news from Finnhub — not tied to a specific ticker.

    Substitutes Benzinga market news for the Intelligence Feed.

    Categories: general, forex, crypto, merger.
    Returns a list of article dicts with: headline, summary, source, url, published_at.
    """
    log_provider_call(log, "Finnhub", f"/news?category={category}", "MARKET")

    data = _get("/news", params={"category": category, "minId": 0})

    articles = []
    for item in (data or [])[:limit]:
        ts        = item.get("datetime", 0)
        published = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None
        articles.append({
            "headline":     item.get("headline"),
            "summary":      item.get("summary"),
            "source":       item.get("source"),
            "url":          item.get("url"),
            "published_at": published,
            "ticker":       item.get("related") or None,
            "provider":     "finnhub",
        })
    return articles


def get_basic_financials(ticker: str) -> dict:
    """
    Get Finnhub's financial metrics — a broad set of ratios and trailing figures.
    Useful for enriching FMP data or as a fallback for key ratios.

    Returns a flat dict of metric name → value.
    Key metrics: 52WeekHigh, peBasicExclExtraTTM, roeTTM, revenueGrowthTTMYoy, etc.
    """
    log_provider_call(log, "Finnhub", f"/stock/metric?symbol={ticker}", ticker)

    data = _get("/stock/metric", params={"symbol": ticker, "metric": "all"})

    if not data or "metric" not in data:
        raise ValueError(f"Finnhub returned no financials for {ticker}")

    m = data["metric"]

    def _pct_to_decimal(val):
        """Finnhub returns some ratio fields as percentages (e.g. 5.18 for 5.18%).
        Convert to decimal so fmt_pct displays them correctly."""
        return val / 100 if val is not None else None

    return {
        "ticker":              ticker.upper(),
        "52_week_high":        m.get("52WeekHigh"),
        "52_week_low":         m.get("52WeekLow"),
        "pe_ttm":              m.get("peBasicExclExtraTTM"),
        "ps_ttm":              m.get("psTTM"),
        "pb_quarterly":        m.get("pbQuarterly"),
        "roe_ttm":             _pct_to_decimal(m.get("roeTTM")),
        "roa_ttm":             _pct_to_decimal(m.get("roaTTM")),
        "revenue_growth_yoy":  m.get("revenueGrowthTTMYoy"),   # already decimal
        "eps_growth_yoy":      m.get("epsGrowthTTMYoy"),        # already decimal
        "dividend_yield":      _pct_to_decimal(m.get("currentDividendYieldTTM")),
        "beta":                m.get("beta"),
        "source":              "finnhub",
        "fetched_at":          datetime.now(timezone.utc).isoformat(),
    }


def get_earnings_calendar(ticker: str, days_ahead: int = 90) -> list[dict]:
    """
    Get upcoming earnings dates for a ticker.

    Returns a list of earnings events with: date, estimate_eps, actual_eps (if past).
    """
    from_date = to_date_str()
    to_date   = to_date_str(datetime.now() + timedelta(days=days_ahead))

    log_provider_call(log, "Finnhub", f"/calendar/earnings?symbol={ticker}", ticker)

    data = _get("/calendar/earnings", params={
        "symbol": ticker,
        "from":   from_date,
        "to":     to_date,
    })

    events = []
    for item in (data.get("earningsCalendar") or []):
        events.append({
            "ticker":       ticker.upper(),
            "date":         item.get("date"),
            "hour":         item.get("hour"),     # "bmo" (before market), "amc" (after), "dmh"
            "eps_estimate": item.get("epsEstimate"),
            "eps_actual":   item.get("epsActual"),
            "revenue_est":  item.get("revenueEstimate"),
            "revenue_act":  item.get("revenueActual"),
            "provider":     "finnhub",
        })

    return events
