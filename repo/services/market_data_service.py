"""
market_data_service.py — Live price and market data for pages.

Pages call these functions directly. This service handles:
  - Checking the cache before making any API call
  - Trying providers in fallback order (Polygon → Finnhub → FMP → yfinance)
  - Returning standardised dicts that pages can use without modification

Functions:
  get_market_indices()          → S&P 500, NASDAQ, Dow, VIX
  get_sector_performance()      → sector % change (via sector ETFs)
  get_live_price(ticker)        → single stock price with change%
  get_watchlist_prices(tickers) → bulk price fetch for watchlist
  get_portfolio_prices(tickers) → same as watchlist (alias)
  get_candles(ticker, period)   → OHLCV history for charts
"""

import providers.polygon_provider  as polygon
import providers.finnhub_provider  as finnhub
import providers.fmp_provider      as fmp
import providers.yfinance_provider as yfinance

from services import _try_providers
from storage.cache_manager import cache
from config.settings import CACHE_TTL, SECTOR_ETFS
from utils.logging_utils import get_logger, log_cache_hit, log_cache_miss
from utils.date_utils import n_days_ago_str, to_date_str

log = get_logger(__name__)


def get_market_indices() -> list[dict] | None:
    """
    Return current values for S&P 500, NASDAQ, Dow Jones, and VIX.
    Each item: {name, value, change_pct, source, fetched_at}

    Fallback: Polygon → yfinance
    """
    cache_key = "indices:all"
    ttl       = CACHE_TTL["indices"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    result, source, _ = _try_providers([
        ("polygon",  polygon.get_index_snapshots),
        ("yfinance", yfinance.get_index_snapshots),
    ], "market indices")

    if result:
        cache.set(cache_key, result, ttl)

    return result


def get_sector_performance() -> dict[str, float] | None:
    """
    Return today's % change for each major sector.
    e.g. {"Technology": 0.82, "Healthcare": -0.34, ...}

    Uses sector ETFs (XLK, XLV, etc.) as proxies for each sector.
    Fallback: Polygon bulk → yfinance individual calls
    """
    cache_key = "sector:performance"
    ttl       = CACHE_TTL["sector_perf"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    etf_tickers   = list(SECTOR_ETFS.values())
    etf_to_sector = {v: k for k, v in SECTOR_ETFS.items()}

    # Try Polygon bulk snapshot (1 API call for all ETFs)
    snapshots = None
    try:
        snapshots = polygon.get_multiple_snapshots(etf_tickers)
    except Exception as e:
        log.warning(f"Polygon sector bulk failed: {e} — trying yfinance")
        try:
            snapshots = {t: yfinance.get_quote(t) for t in etf_tickers}
        except Exception as e2:
            log.error(f"All sector performance providers failed: {e2}")
            return None

    if not snapshots:
        return None

    # Map ETF ticker → sector name, convert decimal to percentage
    sector_perf = {}
    for etf_ticker, data in snapshots.items():
        if data and data.get("change_pct") is not None:
            sector_name = etf_to_sector.get(etf_ticker, etf_ticker)
            sector_perf[sector_name] = round(data["change_pct"] * 100, 2)

    if sector_perf:
        cache.set(cache_key, sector_perf, ttl)

    return sector_perf


def get_live_price(ticker: str) -> dict | None:
    """
    Return current price, change%, and volume for a single stock.
    Result: {ticker, price, change_pct, volume, source, fallback_used, fetched_at}

    Fallback: Polygon → Finnhub → FMP → yfinance
    """
    ticker    = ticker.upper()
    cache_key = f"price:{ticker}"
    ttl       = CACHE_TTL["live_price"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    result, source, fallback_used = _try_providers([
        ("polygon",  lambda: polygon.get_snapshot(ticker)),
        ("finnhub",  lambda: finnhub.get_quote(ticker)),
        ("fmp",      lambda: fmp.get_quote(ticker)),
        ("yfinance", lambda: yfinance.get_quote(ticker)),
    ], f"{ticker} price")

    if result:
        result["source"]        = source
        result["fallback_used"] = fallback_used
        cache.set(cache_key, result, ttl)

    return result


def get_watchlist_prices(tickers: list[str]) -> dict[str, dict]:
    """
    Return prices for a list of tickers.
    Uses Polygon's bulk endpoint (1 API call) where possible.

    Returns: {"MSFT": {price, change_pct, ...}, "AAPL": {...}, ...}
    Missing tickers map to None.
    """
    tickers = [t.upper() for t in tickers]

    # Check what's already cached
    results      = {}
    needs_fetch  = []
    for ticker in tickers:
        cached = cache.get(f"price:{ticker}", CACHE_TTL["live_price"])
        if cached:
            log_cache_hit(log, f"price:{ticker}")
            results[ticker] = cached
        else:
            needs_fetch.append(ticker)

    if not needs_fetch:
        return results

    # Try Polygon bulk for uncached tickers (1 API call)
    try:
        bulk = polygon.get_multiple_snapshots(needs_fetch)
        for ticker, data in bulk.items():
            data["source"]        = "polygon"
            data["fallback_used"] = False
            cache.set(f"price:{ticker}", data, CACHE_TTL["live_price"])
            results[ticker] = data
        # Mark any that Polygon didn't return
        needs_fetch = [t for t in needs_fetch if t not in bulk]
    except Exception as e:
        log.warning(f"Polygon bulk snapshot failed: {e} — falling back to individual calls")

    # Individual fallback calls for anything still missing
    for ticker in needs_fetch:
        results[ticker] = get_live_price(ticker)

    return results


def get_portfolio_prices(tickers: list[str]) -> dict[str, dict]:
    """Alias for get_watchlist_prices — portfolio uses the same price logic."""
    return get_watchlist_prices(tickers)


def get_candles(ticker: str, period: str = "1y") -> list[dict]:
    """
    Return daily OHLCV candles for charting.
    Each item: {date, open, high, low, close, volume}

    Args:
        ticker: e.g. "MSFT"
        period: "1m" | "3m" | "6m" | "1y" | "2y" | "5y"

    Fallback: Polygon → yfinance
    """
    ticker    = ticker.upper()
    cache_key = f"candles:{ticker}:{period}"
    ttl       = CACHE_TTL["candles_daily"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    # Convert period label to number of calendar days for Polygon
    days_map = {"1m": 35, "3m": 95, "6m": 185, "1y": 370, "2y": 740, "5y": 1830}
    days     = days_map.get(period, 370)
    from_date = n_days_ago_str(days)
    to_date   = to_date_str()

    yf_period_map = {"1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"}
    yf_period = yf_period_map.get(period, "1y")

    result, _, _ = _try_providers([
        ("polygon",  lambda: polygon.get_candles(ticker, from_date, to_date)),
        ("yfinance", lambda: yfinance.get_candles(ticker, period=yf_period)),
    ], f"{ticker} candles")

    candles = result or []
    if candles:
        cache.set(cache_key, candles, ttl)

    return candles
