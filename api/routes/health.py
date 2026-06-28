"""
health.py — /api/health/providers endpoint.

Tests each data provider's live connectivity by making a lightweight
single-ticker quote call and measuring latency. Used by the Settings
page to show real integration status instead of hardcoded values.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter

from config.api_keys import (
    POLYGON_API_KEY, FINNHUB_API_KEY, FMP_API_KEY, FRED_API_KEY,
)
import providers.polygon_provider  as polygon
import providers.finnhub_provider  as finnhub
import providers.fmp_provider      as fmp
import providers.yfinance_provider as yfinance_prov

router = APIRouter()

# ── Provider definitions ──────────────────────────────────────────────────────

_PROVIDERS = [
    {
        "id":          "polygon",
        "name":        "Polygon.io",
        "description": "Primary prices & candles",
        "has_key":     bool(POLYGON_API_KEY),
        "test_fn":     lambda: polygon.get_snapshot("AAPL"),
    },
    {
        "id":          "finnhub",
        "name":        "Finnhub",
        "description": "News, earnings & backup prices",
        "has_key":     bool(FINNHUB_API_KEY),
        "test_fn":     lambda: finnhub.get_quote("AAPL"),
    },
    {
        "id":          "fmp",
        "name":        "Financial Modeling Prep",
        "description": "Financials, ratios & analyst data",
        "has_key":     bool(FMP_API_KEY),
        "test_fn":     lambda: fmp.get_quote("AAPL"),
    },
    {
        "id":          "yfinance",
        "name":        "yfinance",
        "description": "Free fallback — no key required",
        "has_key":     True,
        "test_fn":     lambda: yfinance_prov.get_quote("AAPL"),
    },
    {
        "id":          "fred",
        "name":        "FRED (Federal Reserve)",
        "description": "Macro economic indicators",
        "has_key":     bool(FRED_API_KEY),
        "test_fn":     None,   # key-only check, no live test
    },
]


def _run_test(provider: dict) -> dict:
    """
    Run a live connectivity test for one provider.
    Returns a status dict: connected | no_key | error, with latency_ms.
    """
    if not provider["has_key"]:
        return {
            "id":          provider["id"],
            "name":        provider["name"],
            "description": provider["description"],
            "status":      "no_key",
            "latency_ms":  None,
        }

    test_fn = provider.get("test_fn")

    if test_fn is None:
        return {
            "id":          provider["id"],
            "name":        provider["name"],
            "description": provider["description"],
            "status":      "connected",
            "latency_ms":  None,
        }

    start = time.monotonic()
    error_detail = None
    try:
        result = test_fn()
        latency_ms = int((time.monotonic() - start) * 1000)
        status = "connected" if result else "error"
        if not result:
            error_detail = "Provider returned empty response"
    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        status = "error"
        error_detail = str(e)

    return {
        "id":           provider["id"],
        "name":         provider["name"],
        "description":  provider["description"],
        "status":       status,
        "latency_ms":   latency_ms if status == "connected" else None,
        "error_detail": error_detail,
    }


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/providers")
def get_provider_health():
    """
    Test each data provider in parallel and return live connectivity status.
    Uses a lightweight AAPL quote per provider with a 6-second total timeout.
    """
    results = [None] * len(_PROVIDERS)

    with ThreadPoolExecutor(max_workers=4) as pool:
        future_to_idx = {
            pool.submit(_run_test, p): i
            for i, p in enumerate(_PROVIDERS)
        }
        for future in as_completed(future_to_idx, timeout=15):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception:
                p = _PROVIDERS[idx]
                results[idx] = {
                    "id":          p["id"],
                    "name":        p["name"],
                    "description": p["description"],
                    "status":      "error",
                    "latency_ms":  None,
                }

    # Fill any that timed out
    for i, r in enumerate(results):
        if r is None:
            p = _PROVIDERS[i]
            results[i] = {
                "id":          p["id"],
                "name":        p["name"],
                "description": p["description"],
                "status":      "error",
                "latency_ms":  None,
            }

    return results
