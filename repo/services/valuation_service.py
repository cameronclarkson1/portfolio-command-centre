"""
valuation_service.py — Relative valuation model.

Takes inputs from fundamentals_service and runs relative valuation.
Returns fair value estimates with confidence scores and plain-English warnings.

Functions:
  run_relative_valuation(ticker) → sector comparison summary
"""

from services.fundamentals_service import get_key_ratios
from storage.cache_manager import cache
from config.settings import CACHE_TTL
from utils.logging_utils import get_logger, log_cache_hit, log_cache_miss

log = get_logger(__name__)


def run_relative_valuation(ticker: str) -> dict:
    """
    Return key valuation multiples with a brief assessment of whether
    the stock looks cheap, fair, or expensive on each metric.

    This is not a full peer comparison (that requires sector data in Stage 4).
    Instead it compares each multiple against rough S&P 500 averages.

    Returns:
    {
        "ticker":   "MSFT",
        "multiples": {
            "pe_ratio":  {"value": 32.1, "sp500_avg": 22.0, "assessment": "Expensive"},
            "ev_ebitda": {"value": 20.4, "sp500_avg": 13.5, "assessment": "Expensive"},
            "ps_ratio":  {"value": 12.8, "sp500_avg":  2.5, "assessment": "Expensive"},
        },
        "overall_assessment": "Trading at a premium to the S&P 500 on all metrics.",
        "confidence": 65.0,
    }
    """
    ticker    = ticker.upper()
    cache_key = f"rel_val:{ticker}"
    ttl       = CACHE_TTL["valuation"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    ratios = get_key_ratios(ticker)
    if not ratios:
        return {"ticker": ticker, "multiples": {}, "confidence": 0.0}

    # Rough S&P 500 historical averages (update annually)
    sp500_benchmarks = {
        "pe_ratio":  22.0,
        "ev_ebitda": 13.5,
        "ps_ratio":   2.5,
        "pb_ratio":   3.5,
    }

    def _assess(value, benchmark) -> str:
        if value is None or benchmark is None:
            return "N/A"
        ratio = value / benchmark
        if ratio > 1.5:  return "Expensive"
        if ratio > 1.1:  return "Slightly expensive"
        if ratio > 0.9:  return "Fair value"
        if ratio > 0.7:  return "Slightly cheap"
        return "Cheap"

    multiples = {}
    for metric, benchmark in sp500_benchmarks.items():
        value = ratios.get(metric)
        multiples[metric] = {
            "value":      value,
            "sp500_avg":  benchmark,
            "assessment": _assess(value, benchmark),
        }

    # Simple overall summary
    assessments = [m["assessment"] for m in multiples.values() if m["assessment"] != "N/A"]
    expensive_count = sum(1 for a in assessments if "Expensive" in a)
    cheap_count     = sum(1 for a in assessments if "cheap" in a.lower())

    if expensive_count >= 3:
        overall = "Trading at a significant premium to S&P 500 averages on most metrics."
    elif expensive_count >= 2:
        overall = "Trading at a moderate premium on most metrics."
    elif cheap_count >= 2:
        overall = "Trading at a discount to S&P 500 averages — potential value opportunity."
    else:
        overall = "Trading near S&P 500 average multiples — fair value range."

    result = {
        "ticker":              ticker,
        "multiples":           multiples,
        "overall_assessment":  overall,
        "source":              ratios.get("source", "fmp"),
        "confidence":          65.0,  # relative valuation is inherently approximate
    }

    cache.set(cache_key, result, ttl)
    return result
