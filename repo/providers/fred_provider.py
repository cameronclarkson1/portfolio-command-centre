"""
fred_provider.py — Raw API calls to FRED (Federal Reserve Economic Data).

Primary source for all macro indicators:
  - Interest rates (Fed Funds, 10Y Treasury, 2Y Treasury)
  - Inflation (CPI)
  - Unemployment rate
  - GDP growth

Free API — just needs a key from fred.stlouisfed.org.
"""

import requests
from datetime import datetime, timezone

from config.api_keys import FRED_API_KEY
from config.settings import FRED_BASE, REQUEST_TIMEOUT, FRED_SERIES
from utils.logging_utils import get_logger, log_provider_call

log = get_logger(__name__)


def _get(endpoint: str, params: dict = None) -> dict:
    """Make a GET request to FRED. Raises ValueError if no API key."""
    if not FRED_API_KEY:
        raise ValueError("FRED_API_KEY not configured")

    url = f"{FRED_BASE}{endpoint}"
    all_params = {
        "api_key":   FRED_API_KEY,
        "file_type": "json",
        **(params or {}),
    }

    resp = requests.get(url, params=all_params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_series_latest(series_id: str) -> dict:
    """
    Get the most recent observation for a single FRED data series.

    Args:
        series_id: FRED series ID, e.g. "DGS10" for 10-Year Treasury yield.

    Returns a dict with: series_id, value, period (date), source, fetched_at
    """
    log_provider_call(log, "FRED", f"/series/observations?series_id={series_id}")

    data = _get("/series/observations", params={
        "series_id":  series_id,
        "sort_order": "desc",
        "limit":      5,  # grab a few in case the latest is missing (FRED sometimes has '.')
    })

    observations = data.get("observations", [])
    if not observations:
        raise ValueError(f"FRED returned no data for series {series_id}")

    # Find the first observation with a real number value (FRED uses "." for missing)
    value = None
    period = None
    for obs in observations:
        try:
            value = float(obs["value"])
            period = obs["date"]
            break
        except (ValueError, KeyError):
            continue

    if value is None:
        raise ValueError(f"FRED series {series_id} has no numeric value in recent observations")

    return {
        "series_id":  series_id,
        "value":      value,
        "period":     period,
        "source":     "fred",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_series_history(series_id: str, limit: int = 24) -> list[dict]:
    """
    Get recent historical observations for a FRED series.
    Useful for plotting yield curve changes over time.

    Args:
        series_id: FRED series ID
        limit:     Number of most recent observations to return

    Returns a list of dicts with: date, value
    """
    log_provider_call(log, "FRED", f"/series/observations?series_id={series_id}&limit={limit}")

    data = _get("/series/observations", params={
        "series_id":  series_id,
        "sort_order": "desc",
        "limit":      limit,
    })

    history = []
    for obs in data.get("observations", []):
        try:
            history.append({
                "date":  obs["date"],
                "value": float(obs["value"]),
            })
        except (ValueError, KeyError):
            continue  # Skip missing values (FRED uses "." for them)

    return history


def get_macro_snapshot() -> dict:
    """
    Fetch all key macro indicators in one call (makes one request per series).

    Returns a dict keyed by friendly name:
    {
        "fed_funds_rate": {"value": 5.33, "period": "2026-04-01", ...},
        "treasury_10y":   {"value": 4.52, ...},
        ...
    }

    Note: This makes 5 individual FRED API calls — results are cached
    aggressively (1 hour TTL) to avoid hammering the API on every page load.
    """
    snapshot = {}

    for friendly_name, series_id in FRED_SERIES.items():
        try:
            result = get_series_latest(series_id)
            snapshot[friendly_name] = result
        except Exception as e:
            log.warning(f"FRED: could not fetch {friendly_name} ({series_id}): {e}")
            snapshot[friendly_name] = None

    return snapshot
