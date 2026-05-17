"""
data_quality_service.py — Confidence scores and source audit panel.

Aggregates data from all other services to answer:
  "How much should I trust this data?"
  "Where did each number come from?"

Functions:
  get_data_confidence_score(ticker) → confidence % per data type
  get_source_audit(ticker)          → full audit panel for stock research page
"""

from storage.cache_manager import cache
from storage.database import get_connection
from config.settings import CACHE_TTL
from utils.logging_utils import get_logger, log_cache_hit, log_cache_miss
from utils.date_utils import now_utc, ago_str, parse_iso

log = get_logger(__name__)


def get_data_confidence_score(ticker: str) -> dict:
    """
    Return confidence scores for each data type for a ticker.

    Confidence is calculated per type based on:
      - Whether the primary provider was used (vs fallback)
      - How fresh the cached data is
      - How complete the key fields are
      - Whether cross-source validation passed

    Returns:
    {
        "ticker":         "MSFT",
        "price":          95.0,
        "fundamentals":   82.0,
        "valuation":      68.0,
        "news_events":    75.0,
        "macro":          85.0,
        "sec_validation": 90.0,
        "overall":        82.5,    # simple average
        "last_updated":   "2026-05-14T08:00:00Z",
    }
    """
    ticker    = ticker.upper()
    cache_key = f"confidence:{ticker}"
    ttl       = 300  # re-calculate every 5 minutes

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    scores = {"ticker": ticker}

    # ── Price confidence ──────────────────────────────────────────────────────
    price_data = cache.get(f"price:{ticker}", CACHE_TTL["live_price"])
    if price_data:
        primary_ok  = not price_data.get("fallback_used", True)
        scores["price"] = 95.0 if primary_ok else 75.0
    else:
        scores["price"] = 0.0

    # ── Fundamentals confidence ───────────────────────────────────────────────
    fin_data = cache.get(f"financials:{ticker}", CACHE_TTL["fundamentals"])
    if fin_data:
        scores["fundamentals"] = fin_data.get("confidence", 70.0)
    else:
        scores["fundamentals"] = 0.0

    # ── Valuation confidence ──────────────────────────────────────────────────
    dcf_data = cache.get(f"dcf:{ticker}", CACHE_TTL["valuation"])
    if dcf_data:
        scores["valuation"] = dcf_data.get("confidence", 50.0)
    else:
        scores["valuation"] = 0.0

    # ── News/event confidence ─────────────────────────────────────────────────
    news_data = cache.get(f"news:{ticker}:7d", CACHE_TTL["news"])
    if news_data:
        # Finnhub primary = 75, FMP fallback = 65
        providers_used = set(n.get("provider", "") for n in news_data)
        scores["news_events"] = 75.0 if "finnhub" in providers_used else 65.0
    else:
        scores["news_events"] = 0.0

    # ── Macro confidence ──────────────────────────────────────────────────────
    macro_data = cache.get("macro:snapshot", CACHE_TTL["macro"])
    if macro_data:
        scores["macro"] = macro_data.get("confidence", 75.0)
    else:
        scores["macro"] = 0.0

    # ── SEC validation confidence ─────────────────────────────────────────────
    sec_data = cache.get(f"sec_validation:{ticker}", CACHE_TTL["sec_filing"])
    if sec_data and sec_data.get("validation_run"):
        agreement = sec_data.get("agreement_rate") or 0
        scores["sec_validation"] = round(agreement * 100, 1)
    else:
        scores["sec_validation"] = None  # not yet run

    # ── Overall (average of available scores) ─────────────────────────────────
    available = [v for v in scores.values() if isinstance(v, (int, float)) and v > 0]
    scores["overall"]      = round(sum(available) / len(available), 1) if available else 0.0
    scores["last_updated"] = now_utc().isoformat()

    cache.set(cache_key, scores, ttl)
    return scores


def get_source_audit(ticker: str) -> dict:
    """
    Return the full data audit panel for a ticker.

    This is what the "Data Audit" section on the stock research page displays.

    Returns:
    {
        "ticker":   "MSFT",
        "sources": {
            "price":        {"provider": "polygon", "freshness": "2m ago", "label": "Live"},
            "candles":      {"provider": "polygon", "freshness": "45m ago", "label": "Fresh"},
            "fundamentals": {"provider": "fmp",     "freshness": "4d ago",  "label": "Fresh"},
            "filings":      {"provider": "sec_edgar","freshness": "4d ago", "label": "Fresh"},
            "news":         {"provider": "finnhub", "freshness": "12m ago", "label": "Live"},
            "macro":        {"provider": "fred",    "freshness": "2h ago",  "label": "Fresh"},
            "events":       {"provider": "finnhub+gdelt","freshness": "28m ago","label": "Fresh"},
        },
        "confidence": { ... },   # from get_data_confidence_score()
        "warnings": [...],       # all warnings collected across services
        "sec_validated": True,
        "agreement_rate": 1.0,
    }
    """
    ticker    = ticker.upper()
    cache_key = f"audit:{ticker}"
    ttl       = 300

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    sources  = {}
    warnings = []

    def _read_cache_meta(key: str, cache_ttl: int) -> dict:
        """Get source and freshness metadata from a cached value."""
        data = cache.get(key, cache_ttl)
        if not data:
            return {"provider": "not loaded", "freshness": "not loaded", "label": "Missing"}
        fetched_at = parse_iso(
            data.get("fetched_at") if isinstance(data, dict) else None
        )
        return {
            "provider":  (data.get("source") or "unknown") if isinstance(data, dict) else "various",
            "freshness": ago_str(fetched_at),
            "label":     "Live" if fetched_at and (now_utc() - fetched_at.replace(
                tzinfo=fetched_at.tzinfo or __import__("datetime").timezone.utc
            )).total_seconds() < 120 else "Fresh",
        }

    sources["price"]        = _read_cache_meta(f"price:{ticker}",          CACHE_TTL["live_price"])
    sources["candles"]      = _read_cache_meta(f"candles:{ticker}:1y",     CACHE_TTL["candles_daily"])
    sources["fundamentals"] = _read_cache_meta(f"financials:{ticker}",     CACHE_TTL["fundamentals"])
    sources["news"]         = _read_cache_meta(f"news:{ticker}:7d",        CACHE_TTL["news"])
    sources["macro"]        = _read_cache_meta("macro:snapshot",           CACHE_TTL["macro"])

    # SEC validation status
    sec_data = cache.get(f"sec_validation:{ticker}", CACHE_TTL["sec_filing"])
    if sec_data and sec_data.get("validation_run"):
        sources["filings"] = {
            "provider":  "sec_edgar",
            "freshness": "validated",
            "label":     "Validated",
        }
        warnings.extend(sec_data.get("warnings", []))
        sec_validated  = True
        agreement_rate = sec_data.get("agreement_rate")
    else:
        sources["filings"] = {"provider": "sec_edgar", "freshness": "not run", "label": "Pending"}
        sec_validated      = False
        agreement_rate     = None

    # Collect warnings from other cached data
    dcf_data = cache.get(f"dcf:{ticker}", CACHE_TTL["valuation"])
    if dcf_data:
        warnings.extend(dcf_data.get("warnings", []))

    confidence = get_data_confidence_score(ticker)

    result = {
        "ticker":         ticker,
        "sources":        sources,
        "confidence":     confidence,
        "warnings":       list(dict.fromkeys(warnings)),   # deduplicate warnings
        "sec_validated":  sec_validated,
        "agreement_rate": agreement_rate,
        "generated_at":   now_utc().isoformat(),
    }

    cache.set(cache_key, result, ttl)
    return result
