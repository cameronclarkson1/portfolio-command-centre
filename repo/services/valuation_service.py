"""
valuation_service.py — DCF and relative valuation models.

Takes inputs from fundamentals_service and runs financial models.
Returns fair value estimates with confidence scores and plain-English warnings.

Functions:
  run_dcf_model(ticker)          → fair value, upside, confidence, warnings
  run_relative_valuation(ticker) → sector comparison summary
"""

from services.fundamentals_service import get_valuation_inputs, get_key_ratios
from services import _try_providers
from storage.cache_manager import cache
from storage.database import get_connection
from config.settings import CACHE_TTL
from utils.logging_utils import get_logger, log_cache_hit, log_cache_miss
from utils.date_utils import now_utc

import json

log = get_logger(__name__)


def run_dcf_model(ticker: str) -> dict:
    """
    Run a 2-stage Discounted Cash Flow model for a ticker.

    Stage 1: 5 years of projected free cash flows at the estimated growth rate.
    Stage 2: Terminal value using the Gordon Growth Model.

    Returns:
    {
        "ticker":          "MSFT",
        "fair_value":       365.20,
        "current_price":    None,      # filled by page from market_data_service
        "upside_pct":       None,      # filled by page once price is known
        "model":           "dcf",
        "inputs_used": {
            "revenue_growth": 0.14,
            "ebit_margin":    0.44,
            "wacc":           0.087,
            "terminal_growth":0.03,
        },
        "confidence":      72.0,       # lower if inputs are estimated
        "warnings":        ["Tax rate defaulted to 20%", ...],
        "completeness":    0.85,
    }

    Returns a dict with fair_value=None and a warning if key inputs are missing.
    """
    ticker    = ticker.upper()
    cache_key = f"dcf:{ticker}"
    ttl       = CACHE_TTL["valuation"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    inputs   = get_valuation_inputs(ticker)
    warnings = list(inputs.get("warnings", []))

    # Check if we have enough to run a DCF at all
    if not inputs.get("free_cash_flow") or not inputs.get("shares_out"):
        result = {
            "ticker":      ticker,
            "fair_value":  None,
            "model":       "dcf",
            "confidence":  0.0,
            "warnings":    warnings + ["DCF cannot run — free cash flow or share count missing"],
            "completeness": inputs.get("completeness", 0.0),
        }
        return result

    fcf           = inputs["free_cash_flow"]
    growth_rate   = inputs.get("revenue_growth") or 0.08   # default 8% if missing
    wacc          = inputs.get("wacc_estimate",   0.09)
    terminal_g    = inputs.get("terminal_growth", 0.03)
    net_debt      = inputs.get("net_debt",        0)
    shares_out    = inputs["shares_out"]

    if inputs.get("revenue_growth") is None:
        warnings.append(f"Revenue growth not available — defaulted to 8% for DCF projection")

    # ── Stage 1: 5-year FCF projections ──────────────────────────────────────
    pv_fcfs = []
    projected_fcf = fcf
    for year in range(1, 6):
        projected_fcf *= (1 + growth_rate)
        pv = projected_fcf / ((1 + wacc) ** year)
        pv_fcfs.append(pv)

    # ── Stage 2: Terminal value (Gordon Growth Model) ─────────────────────────
    if wacc <= terminal_g:
        warnings.append("WACC ≤ terminal growth rate — terminal value calculation invalid, set to 0")
        terminal_value = 0
    else:
        terminal_fcf   = projected_fcf * (1 + terminal_g)
        terminal_value = terminal_fcf / (wacc - terminal_g)

    pv_terminal = terminal_value / ((1 + wacc) ** 5)

    # ── Enterprise value → equity value → per share ───────────────────────────
    enterprise_value = sum(pv_fcfs) + pv_terminal
    equity_value     = enterprise_value - net_debt
    fair_value       = equity_value / shares_out if shares_out else None

    # ── Confidence score ──────────────────────────────────────────────────────
    # Start at 85% and reduce for each estimation/warning
    base_confidence   = 85.0
    penalty_per_warn  = 5.0
    data_warnings     = [w for w in warnings if "defaulted" in w or "missing" in w or "unavailable" in w]
    confidence = max(20.0, base_confidence - len(data_warnings) * penalty_per_warn)
    confidence = round(confidence * inputs.get("completeness", 0.8), 1)

    result = {
        "ticker":      ticker,
        "fair_value":  round(fair_value, 2) if fair_value else None,
        "model":       "dcf",
        "inputs_used": {
            "fcf_base":       round(fcf, 0),
            "revenue_growth": round(growth_rate, 4),
            "wacc":           round(wacc, 4),
            "terminal_growth": terminal_g,
            "net_debt":       net_debt,
            "shares_out":     shares_out,
        },
        "pv_stage1":   round(sum(pv_fcfs), 0),
        "pv_terminal": round(pv_terminal, 0),
        "confidence":  confidence,
        "warnings":    warnings,
        "completeness": inputs.get("completeness", 0.0),
    }

    cache.set(cache_key, result, ttl)

    # Save to database so we can track changes over time
    _save_valuation_to_db(ticker, result)

    return result


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


def _save_valuation_to_db(ticker: str, result: dict):
    """Save DCF output to database so we can track how fair value changes over time."""
    try:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO valuation_outputs
                (ticker, model, fair_value, confidence, inputs_json, warnings_json, source, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker,
                result.get("model"),
                result.get("fair_value"),
                result.get("confidence"),
                json.dumps(result.get("inputs_used"), default=str),
                json.dumps(result.get("warnings"),    default=str),
                "fmp+fred",
                now_utc().isoformat(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning(f"Could not save valuation to database: {e}")
