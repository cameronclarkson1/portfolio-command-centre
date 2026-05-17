"""
polygon_provider.py — Raw API calls to Polygon.io.

Primary source for: live/delayed US stock prices, OHLCV candles,
major index values (S&P 500, NASDAQ, Dow, VIX), and sector ETF prices.

Free tier: 15-minute delayed data, 5 API calls/minute.
Paid tier: real-time data, unlimited calls.
"""

import requests
from datetime import datetime, timezone

from config.api_keys import POLYGON_API_KEY
from config.settings import POLYGON_BASE, REQUEST_TIMEOUT, INDEX_TICKERS
from utils.logging_utils import get_logger, log_provider_call

log = get_logger(__name__)


def _get(endpoint: str, params: dict = None) -> dict:
    """
    Make a GET request to Polygon.
    Raises ValueError if no API key is configured.
    Raises requests.HTTPError if the server returns an error status.
    """
    if not POLYGON_API_KEY:
        raise ValueError("POLYGON_API_KEY not configured")

    url = f"{POLYGON_BASE}{endpoint}"
    all_params = {"apiKey": POLYGON_API_KEY, **(params or {})}

    resp = requests.get(url, params=all_params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_snapshot(ticker: str) -> dict:
    """
    Get current price data for a single US stock or ETF.
    Includes today's % change from previous close.

    Returns a dict with: ticker, price, change_pct, volume, source, fetched_at
    """
    log_provider_call(log, "Polygon", f"/v2/snapshot/.../{ticker}", ticker)

    data = _get(f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}")

    t = data.get("ticker", {})

    # Best available current price: most recent trade → today's close → prev close
    price = (
        (t.get("lastTrade") or {}).get("p")
        or (t.get("min") or {}).get("c")
        or (t.get("day") or {}).get("c")
    )

    # todaysChangePerc is already calculated by Polygon (vs previous close)
    change_pct_raw = t.get("todaysChangePerc", 0.0)
    change_pct = change_pct_raw / 100  # convert 1.22 → 0.0122

    return {
        "ticker":     ticker.upper(),
        "price":      price,
        "change_pct": change_pct,
        "volume":     (t.get("day") or {}).get("v"),
        "source":     "polygon",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_candles(ticker: str, from_date: str, to_date: str, timespan: str = "day") -> list[dict]:
    """
    Get OHLCV candles for a ticker between two dates.

    Args:
        ticker:    Stock ticker, e.g. "MSFT" or index e.g. "I:SPX"
        from_date: Start date as "YYYY-MM-DD"
        to_date:   End date as "YYYY-MM-DD"
        timespan:  "minute" | "hour" | "day" | "week" | "month"

    Returns a list of dicts, each with: date, open, high, low, close, volume
    """
    log_provider_call(log, "Polygon", f"/v2/aggs/{ticker}/range/1/{timespan}/{from_date}/{to_date}", ticker)

    data = _get(
        f"/v2/aggs/ticker/{ticker}/range/1/{timespan}/{from_date}/{to_date}",
        params={"adjusted": "true", "sort": "asc", "limit": 500},
    )

    candles = []
    for r in data.get("results", []):
        # Polygon timestamps are milliseconds since Unix epoch
        date_str = datetime.fromtimestamp(r["t"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        candles.append({
            "date":   date_str,
            "open":   r.get("o"),
            "high":   r.get("h"),
            "low":    r.get("l"),
            "close":  r.get("c"),
            "volume": r.get("v"),
        })

    return candles


def get_index_snapshots() -> list[dict]:
    """
    Get current values for S&P 500, NASDAQ, Dow Jones, and VIX.
    Uses Polygon's /v3/snapshot endpoint for indices.

    Returns a list of dicts with: name, value, change_pct, source, fetched_at
    """
    tickers_param = ",".join(INDEX_TICKERS.values())  # "I:SPX,I:NDX,I:DJI,I:VIX"
    log_provider_call(log, "Polygon", f"/v3/snapshot?ticker.any_of={tickers_param}")

    data = _get("/v3/snapshot", params={"ticker.any_of": tickers_param})

    # Build a lookup: Polygon ticker → snapshot data
    results_map = {}
    for item in data.get("results", []):
        poly_ticker = item.get("ticker", "")
        session = item.get("session", {})
        change_pct_raw = session.get("changePercent", 0.0)
        results_map[poly_ticker] = {
            "value":      session.get("close") or session.get("price"),
            "change_pct": change_pct_raw / 100,  # convert 1.22 → 0.0122
        }

    now = datetime.now(timezone.utc).isoformat()
    indices = []
    for name, poly_ticker in INDEX_TICKERS.items():
        r = results_map.get(poly_ticker, {})
        indices.append({
            "name":       name,
            "value":      r.get("value"),
            "change_pct": r.get("change_pct", 0.0),
            "source":     "polygon",
            "fetched_at": now,
        })

    return indices


def get_multiple_snapshots(tickers: list[str]) -> dict[str, dict]:
    """
    Get price snapshots for a list of tickers in one API call.
    More efficient than calling get_snapshot() in a loop.

    Returns a dict: { "MSFT": {price, change_pct, ...}, "AAPL": {...}, ... }
    """
    tickers_param = ",".join(t.upper() for t in tickers)
    log_provider_call(log, "Polygon", f"/v2/snapshot/.../tickers?tickers={tickers_param[:40]}...")

    data = _get(
        "/v2/snapshot/locale/us/markets/stocks/tickers",
        params={"tickers": tickers_param},
    )

    results = {}
    now = datetime.now(timezone.utc).isoformat()

    for t in data.get("tickers", []):
        ticker = t.get("ticker", "")
        price = (
            (t.get("lastTrade") or {}).get("p")
            or (t.get("min") or {}).get("c")
            or (t.get("day") or {}).get("c")
        )
        change_pct = t.get("todaysChangePerc", 0.0) / 100

        results[ticker] = {
            "ticker":     ticker,
            "price":      price,
            "change_pct": change_pct,
            "volume":     (t.get("day") or {}).get("v"),
            "source":     "polygon",
            "fetched_at": now,
        }

    return results
