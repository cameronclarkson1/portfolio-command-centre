"""
valuation_engine.py — Sector-aware valuation orchestrator.

For each ticker:
  1. Detects sector and industry from FMP company profile
  2. Maps to a valuation bucket (technology, reit, financials, etc.)
  3. Selects the 3 most appropriate models for that sector
  4. Runs each model with automatic fallbacks
  5. Blends results into a weighted fair value range
  6. Returns a clean result with plain-English explanation

This is the main valuation entry point for all pages.
"""

from services.sector_mapper import (
    get_bucket, is_early_stage,
    BUCKET_WEIGHTS, BUCKET_LABELS, BUCKET_EXPLANATIONS,
)
from services.fundamentals_service import (
    get_financial_statements, get_key_ratios, get_valuation_inputs,
)
from services.dcf_model           import run_dcf
from services.relative_valuation  import run_pe, run_ev_ebitda, run_ev_sales, run_pb, run_pcf
from services.ddm_model           import run_ddm
from services.reit_valuation      import run_pffo, run_paffo
from storage.cache_manager        import cache
from config.settings              import CACHE_TTL
from utils.logging_utils          import get_logger, log_cache_hit, log_cache_miss

import providers.fmp_provider as fmp

log = get_logger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_sector(ticker: str) -> tuple[str, str]:
    """Fetch sector and industry. Tries FMP profile first, then yfinance as fallback."""
    cache_key = f"profile:{ticker}"
    ttl       = CACHE_TTL["fundamentals"]

    cached = cache.get(cache_key, ttl)
    if cached:
        return cached.get("sector", ""), cached.get("industry", "")

    sector, industry = "", ""

    # Primary: FMP company profile
    try:
        profile = fmp.get_company_profile(ticker)
        sector  = profile.get("sector")  or ""
        industry = profile.get("industry") or ""
    except Exception as e:
        log.warning(f"FMP profile failed for {ticker}: {e}")

    # Fallback: yfinance info (free, no key required)
    if not sector:
        try:
            import yfinance as yf
            info     = yf.Ticker(ticker).info
            sector   = info.get("sector")   or ""
            industry = info.get("industry") or ""
            log.info(f"Sector for {ticker} fetched from yfinance fallback: {sector}")
        except Exception as e:
            log.warning(f"yfinance sector fallback failed for {ticker}: {e}")

    cache.set(cache_key, {"sector": sector, "industry": industry}, ttl)
    return sector, industry


def _run_model(model_key: str, bucket: str, ticker: str,
               ratios: dict, statements: dict, price: float,
               val_inputs: dict) -> dict:
    """Dispatch to the correct model function by key. Catches all errors gracefully."""
    try:
        if   model_key == "dcf":      return run_dcf(ticker, bucket, inputs=val_inputs, price=price)
        elif model_key == "pe":       return run_pe(bucket, ratios, statements, price)
        elif model_key == "ev_ebitda":return run_ev_ebitda(bucket, ratios, statements)
        elif model_key == "ev_sales": return run_ev_sales(bucket, ratios, statements, price)
        elif model_key == "pb":       return run_pb(bucket, ratios, statements, price)
        elif model_key == "pcf":      return run_pcf(bucket, ratios, statements, price)
        elif model_key == "ddm":      return run_ddm(ticker, bucket, ratios, statements, price)
        elif model_key == "pffo":     return run_pffo(ratios, statements)
        elif model_key == "paffo":    return run_paffo(ratios, statements)
        else:
            return {"model": model_key, "name": model_key, "fair_value": None,
                    "confidence": 0.0, "inputs_used": {}, "warnings": [f"Unknown model: {model_key}"]}
    except Exception as e:
        log.error(f"Model {model_key} crashed for {ticker}: {e}")
        return {"model": model_key, "name": model_key, "fair_value": None,
                "confidence": 0.0, "inputs_used": {}, "warnings": [f"Model error: {str(e)}"]}


def _blend_results(model_results: dict, weights: dict, price: float) -> dict:
    """
    Combine model outputs into a weighted fair value range.

    - Only models that produced a fair_value are included.
    - Weights are re-normalised if some models failed.
    - Returns low / base / high fair value and a valuation rating.
    """
    valid = {k: v for k, v in model_results.items() if v.get("fair_value")}

    if not valid:
        return {
            "fair_value_low":     None,
            "fair_value_base":    None,
            "fair_value_high":    None,
            "upside_pct":         None,
            "valuation_rating":   "Insufficient data",
            "overall_confidence": 0.0,
            "weights_used":       {},
        }

    # Re-normalise weights to only models that produced a result
    valid_raw    = {k: weights.get(k, 1 / len(valid)) for k in valid}
    total_weight = sum(valid_raw.values())
    norm_weights = {k: w / total_weight for k, w in valid_raw.items()}

    # Weighted average = base fair value
    fair_value_base = sum(valid[k]["fair_value"] * norm_weights[k] for k in valid)

    # Range = lowest and highest model estimate
    all_fvs = [v["fair_value"] for v in valid.values()]

    # Upside vs current price
    upside_pct = (fair_value_base - price) / price if price else None

    # Valuation rating
    if upside_pct is None:
        rating = "Insufficient data"
    elif upside_pct > 0.20:
        rating = "Undervalued"
    elif upside_pct > 0.05:
        rating = "Slightly Undervalued"
    elif upside_pct > -0.05:
        rating = "Fairly Valued"
    elif upside_pct > -0.20:
        rating = "Slightly Overvalued"
    else:
        rating = "Overvalued"

    # Weighted average confidence
    overall_confidence = sum(valid[k]["confidence"] * norm_weights[k] for k in valid)

    return {
        "fair_value_low":     round(min(all_fvs), 2),
        "fair_value_base":    round(fair_value_base, 2),
        "fair_value_high":    round(max(all_fvs), 2),
        "upside_pct":         round(upside_pct, 4) if upside_pct is not None else None,
        "valuation_rating":   rating,
        "overall_confidence": round(overall_confidence, 1),
        "weights_used":       {k: round(norm_weights[k], 3) for k in valid},
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def run_valuation(ticker: str, price: float | None = None) -> dict:
    """
    Run a sector-appropriate valuation for any ticker.

    Returns:
    {
        "ticker":           "O",
        "sector":           "Real Estate",
        "industry":         "REIT - Retail",
        "bucket":           "reit",
        "bucket_label":     "Real Estate / REIT",
        "why_these_models": "This company is classified as a REIT...",
        "models_run": {
            "pffo":  {"name": "P/FFO", "fair_value": 62.50, "confidence": 65.0, ...},
            "paffo": {...},
            "pb":    {...},
        },
        "fair_value_low":     52.0,
        "fair_value_base":    59.8,
        "fair_value_high":    65.0,
        "upside_pct":        -0.028,
        "valuation_rating":  "Fairly Valued",
        "overall_confidence": 63.0,
        "warnings":          [...],
    }
    """
    ticker    = ticker.upper()
    cache_key = f"valuation_v2:{ticker}"
    ttl       = CACHE_TTL.get("valuation", 3600)

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    # 1. Detect sector and industry
    sector, industry = _get_sector(ticker)

    # 2. Fetch all financial data needed by the models
    ratios     = get_key_ratios(ticker)          or {}
    statements = get_financial_statements(ticker) or {}
    val_inputs = get_valuation_inputs(ticker, price=price, sector=sector)

    # 3. Determine valuation bucket (with early-stage override)
    bucket = get_bucket(sector, industry)
    if is_early_stage(ratios, statements):
        bucket = "early_stage"

    # 4. Get model weights for this bucket
    weights = BUCKET_WEIGHTS.get(bucket, BUCKET_WEIGHTS["default"])

    # 5. Run each model
    models_run = {}
    for model_key in weights:
        models_run[model_key] = _run_model(
            model_key, bucket, ticker, ratios, statements, price or 0, val_inputs
        )

    # 6. Cross-validate DCF against relative models — flag it as outlier if extreme
    dcf_result = models_run.get("dcf")
    if dcf_result and dcf_result.get("fair_value"):
        relative_keys = [k for k in models_run if k != "dcf" and models_run[k].get("fair_value")]
        if relative_keys:
            rel_avg = sum(models_run[k]["fair_value"] for k in relative_keys) / len(relative_keys)
            dcf_fv  = dcf_result["fair_value"]
            if rel_avg > 0:
                ratio = dcf_fv / rel_avg
                if ratio > 3.0 or ratio < 0.33:
                    dcf_result["confidence"] = min(dcf_result.get("confidence", 0), 20.0)
                    dcf_result["warnings"].append(
                        f"DCF is {ratio:.1f}× the average of relative models (${rel_avg:,.0f}) — "
                        "significant divergence detected; DCF weight reduced"
                    )
                    # Downweight DCF in blend by slashing its assigned weight
                    weights = dict(weights)
                    if "dcf" in weights:
                        weights["dcf"] = weights["dcf"] * 0.1

    # 7. Blend results into fair value range
    blend = _blend_results(models_run, weights, price or 0)

    # 8. Collect unique warnings across all models
    all_warnings = []
    for result in models_run.values():
        for w in result.get("warnings", []):
            if w not in all_warnings:
                all_warnings.append(w)

    # 9. Adjust confidence and generate explanation
    raw_confidence      = blend.get("overall_confidence", 0.0)
    adjusted_confidence = raw_confidence
    confidence_explanation = ""
    try:
        from services.confidence_service import (
            compute_adjusted_confidence,
            build_confidence_explanation,
        )
        adjusted_confidence = compute_adjusted_confidence(
            base_confidence = raw_confidence,
            model_results   = models_run,
            bucket          = bucket,
            statements      = statements,
            val_inputs      = val_inputs,
        )
        confidence_explanation = build_confidence_explanation(
            model_results      = models_run,
            bucket             = bucket,
            overall_confidence = adjusted_confidence,
            statements         = statements,
            val_inputs         = val_inputs,
        )
    except Exception as e:
        log.warning(f"confidence_service failed for {ticker}: {e}")

    result = {
        "ticker":                 ticker,
        "sector":                 sector   or "Unknown",
        "industry":               industry or "Unknown",
        "bucket":                 bucket,
        "bucket_label":           BUCKET_LABELS.get(bucket, bucket),
        "why_these_models":       BUCKET_EXPLANATIONS.get(bucket, ""),
        "models_run":             models_run,
        **blend,
        "overall_confidence":     adjusted_confidence,   # overrides blend's raw value
        "confidence_explanation": confidence_explanation,
        "warnings":               all_warnings,
    }

    cache.set(cache_key, result, ttl)
    return result
