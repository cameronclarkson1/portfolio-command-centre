"""
macro_service.py — Macroeconomic data and market regime determination.

Pages call these functions for:
  - Interest rates and yield curve (from FRED)
  - Market regime classification (risk-on / Neutral / risk-off / crisis)
  - Inflation, unemployment, GDP data

Functions:
  get_macro_snapshot()    → all key macro indicators with freshness labels
  get_yield_curve_data()  → 2Y, 10Y yields, spread, and status
  get_market_regime()     → regime label, VIX level, buying rules, summary
"""

import providers.fred_provider    as fred
import providers.polygon_provider as polygon
import providers.yfinance_provider as yfinance

from services import _try_providers
from storage.cache_manager import cache
from config.settings import CACHE_TTL, VIX_REGIMES, FRED_SERIES
from utils.logging_utils import get_logger, log_cache_hit, log_cache_miss
from utils.date_utils import ago_str, parse_iso

log = get_logger(__name__)


def get_macro_snapshot() -> dict | None:
    """
    Return all key macro indicators in one dict.

    Structure:
    {
        "fed_funds_rate": {"value": 5.33, "period": "2026-04-01", "source": "fred", ...},
        "treasury_10y":   {"value": 4.52, ...},
        "treasury_2y":    {"value": 4.89, ...},
        "cpi_yoy":        {"value": 3.2,  ...},
        "unemployment":   {"value": 3.8,  ...},
        "gdp_growth":     {"value": 2.1,  ...},
        "fetched_at":     "2026-05-14T...",
        "source":         "fred",
        "confidence":     85.0,
    }

    Fallback: FRED (primary) — no good automatic fallback for macro;
    logs warnings for any series that fails.
    """
    cache_key = "macro:snapshot"
    ttl       = CACHE_TTL["macro"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    try:
        snapshot = fred.get_macro_snapshot()
    except Exception as e:
        log.error(f"FRED macro snapshot failed: {e}")
        return None

    # Count how many series returned real values
    total   = len(FRED_SERIES)
    present = sum(1 for v in snapshot.values() if v is not None)
    confidence = round((present / total) * 85, 1)  # max 85% — macro data is monthly

    snapshot["confidence"] = confidence
    snapshot["source"]     = "fred"

    cache.set(cache_key, snapshot, ttl)
    return snapshot


def get_yield_curve_data() -> dict | None:
    """
    Return 10Y and 2Y Treasury yields, the spread, and an interpretation.

    Structure:
    {
        "treasury_10y":    4.52,
        "treasury_2y":     4.89,
        "spread":          -0.37,
        "status":          "Inverted",   # Normal | Flat | Inverted
        "interpretation":  "An inverted yield curve ...",
        "source":          "fred",
        "confidence":      88.0,
    }
    """
    cache_key = "macro:yield_curve"
    ttl       = CACHE_TTL["yield_curve"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    # Fetch 10Y and 2Y independently so one failure doesn't block both
    y10, y2 = None, None
    try:
        y10 = fred.get_series_latest("DGS10")["value"]
    except Exception as e:
        log.warning(f"FRED 10Y treasury fetch failed: {e}")

    try:
        y2 = fred.get_series_latest("DGS2")["value"]
    except Exception as e:
        log.warning(f"FRED 2Y treasury fetch failed: {e}")

    if y10 is None and y2 is None:
        return None

    spread = round((y10 or 0) - (y2 or 0), 3)

    if spread > 0.5:
        status         = "Normal"
        interpretation = (
            f"10Y–2Y spread is +{spread:.2f}% (positive). "
            "A steep yield curve typically indicates market expectations of growth. "
            "Positive for risk assets and cyclical stocks."
        )
    elif spread > -0.2:
        status         = "Flat"
        interpretation = (
            f"10Y–2Y spread is {spread:+.2f}% (near-flat). "
            "A flat curve signals uncertainty about the economic outlook. "
            "Monitor for movement in either direction."
        )
    else:
        status         = "Inverted"
        interpretation = (
            f"10Y–2Y spread is {spread:.2f}% (inverted). "
            "An inverted yield curve has historically preceded recessions by 12–18 months. "
            "Favour quality and defensive positions. Monitor for steepening as a recovery signal."
        )

    result = {
        "treasury_10y":   y10,
        "treasury_2y":    y2,
        "spread":         spread,
        "status":         status,
        "interpretation": interpretation,
        "source":         "fred",
        "confidence":     90.0 if (y10 and y2) else 50.0,
    }

    cache.set(cache_key, result, ttl)
    return result


def get_market_regime() -> dict | None:
    """
    Classify the current market regime based on VIX level and trend.

    Returns:
    {
        "regime":      "Neutral",       # risk-on | Neutral | risk-off | crisis
        "vix":          21.4,
        "sp500_trend": "Sideways",      # Up | Down | Sideways
        "buying_rule": "Cautious buying only ...",
        "summary":     "VIX at 21 signals ...",
        "source":      "polygon",
        "confidence":  80.0,
    }
    """
    cache_key = "macro:regime"
    ttl       = CACHE_TTL["macro"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    # Get VIX from market indices (already cached there)
    from services.market_data_service import get_market_indices
    indices = get_market_indices()

    vix_value  = None
    sp500_chg  = None
    source     = "yfinance"

    if indices:
        for idx in indices:
            if idx["name"] == "VIX":
                vix_value = idx.get("value")
                source    = idx.get("source", "yfinance")
            if idx["name"] == "S&P 500":
                sp500_chg = idx.get("change_pct")

    if vix_value is None:
        log.warning("Could not determine VIX — regime unknown")
        return None

    # Classify regime using VIX thresholds
    regime = "Neutral"
    for label, (low, high) in VIX_REGIMES.items():
        if low <= vix_value < high:
            regime = label
            break

    # S&P 500 trend (rough: based on today's change)
    if sp500_chg is not None:
        if sp500_chg > 0.005:
            sp500_trend = "Up"
        elif sp500_chg < -0.005:
            sp500_trend = "Down"
        else:
            sp500_trend = "Sideways"
    else:
        sp500_trend = "Unknown"

    # Buying rules and summaries per regime
    regime_text = {
        "risk-on": {
            "buying_rule": "Full position building allowed. Valuation discipline still applies.",
            "summary": (
                f"VIX at {vix_value:.1f} signals low fear — risk-on conditions. "
                "Normal buying conditions are in effect. Build positions in high-conviction ideas."
            ),
        },
        "Neutral": {
            "buying_rule": "Cautious buying only — prefer adds to existing positions over new initiations.",
            "summary": (
                f"VIX at {vix_value:.1f} signals moderate uncertainty. "
                "Cautious buying is appropriate. Avoid initiating large new positions "
                "until a clearer trend emerges."
            ),
        },
        "risk-off": {
            "buying_rule": "Restrict new buys. Focus on capital preservation. Consider raising cash.",
            "summary": (
                f"VIX at {vix_value:.1f} signals elevated fear — risk-off conditions. "
                "Restrict new positions. Hold quality and raise cash above target level."
            ),
        },
        "crisis": {
            "buying_rule": "Preserve capital only. No aggressive buying. Large cash position required.",
            "summary": (
                f"VIX at {vix_value:.1f} — crisis conditions. "
                "Capital preservation is the only priority. Hold maximum cash. "
                "Only consider highest-quality names at extreme discounts."
            ),
        },
    }

    text = regime_text.get(regime, regime_text["Neutral"])

    result = {
        "regime":      regime,
        "vix":         vix_value,
        "sp500_trend": sp500_trend,
        "buying_rule": text["buying_rule"],
        "summary":     text["summary"],
        "source":      source,
        "confidence":  80.0,
    }

    cache.set(cache_key, result, ttl)
    return result
