"""
confidence_service.py — Generates plain-English explanations for valuation confidence scores.

Stage 1: Explainability only.
  Inspects model results, financial data quality, and model agreement
  to produce a human-readable explanation of the existing overall_confidence score.
  Does NOT modify overall_confidence.

Public API:
  build_confidence_explanation(model_results, bucket, overall_confidence,
                               statements, val_inputs) -> str
"""

from __future__ import annotations
from typing import Optional


# For each sector bucket that has critical models, list the model keys that MUST
# produce a fair_value for the valuation to be fully reliable.
# If the bucket is present but none of the critical models ran, we flag it.
_SECTOR_CRITICAL_MODELS: dict[str, tuple[list[str], str]] = {
    "reit":       (["pffo", "paffo"], "FFO-based model (P/FFO or P/AFFO)"),
    "financials": (["pb"],            "Price-to-Book model"),
    "insurance":  (["pb"],            "Price-to-Book model"),
    "early_stage":(["ev_sales"],      "revenue multiple (EV/Sales)"),
}

# Keywords in warning strings that indicate an input was estimated rather than sourced
_ESTIMATION_KEYWORDS = (
    "defaulted", "estimated", "inferred", "unavailable", "missing",
    "derived", "fallback", "assumed", "cannot",
)


def build_confidence_explanation(
    model_results: dict,
    bucket: str,
    overall_confidence: float,
    statements: Optional[dict],
    val_inputs: Optional[dict],
) -> str:
    """
    Return a 1-3 sentence plain-English explanation of the valuation confidence score.

    Parameters
    ----------
    model_results       {model_key: {fair_value, confidence, name, warnings, inputs_used}}
                        Full models_run dict including models that returned fair_value=None.
    bucket              Valuation bucket from sector_mapper, e.g. "technology", "reit".
    overall_confidence  The already-computed weighted-average confidence (0-100).
                        This function never modifies it.
    statements          Dict from get_financial_statements(): contains income, balance,
                        cashflow lists, plus fallback_used (bool) and source (str).
    val_inputs          Dict from get_valuation_inputs(): contains completeness (float),
                        warnings (list[str]), and the DCF inputs.
    """
    positives: list[str] = []
    negatives: list[str] = []

    stmts  = statements or {}
    inputs = val_inputs  or {}

    # ── 1. Count working vs attempted models ─────────────────────────────────
    valid_models = {k: v for k, v in model_results.items() if v.get("fair_value")}
    n_valid = len(valid_models)
    n_total = len(model_results)

    if n_valid == 0:
        return (
            "No valuation models produced a result — "
            "insufficient financial data to estimate fair value."
        )

    if n_valid == 1:
        model_name = list(valid_models.values())[0].get("name", "one model")
        negatives.append(f"only one model ({model_name}) produced a result")
    elif n_valid == n_total and n_total >= 3:
        positives.append(f"all {n_valid} valuation models ran successfully")
    elif n_valid < n_total:
        negatives.append(f"{n_valid} of {n_total} models produced a result")
    else:
        # n_valid == n_total == 2 — neutral, don't pad positives or negatives
        pass

    # ── 2. Model agreement (only meaningful with 2+ results) ─────────────────
    if n_valid >= 2:
        fvs = [v["fair_value"] for v in valid_models.values()]
        lo, hi = min(fvs), max(fvs)
        mid = (lo + hi) / 2
        spread = (hi - lo) / mid if mid > 0 else 0

        if spread <= 0.10:
            positives.append(f"models agree within {spread:.0%} — strong consensus")
        elif spread <= 0.20:
            positives.append(f"models are within {spread:.0%} of each other")
        elif spread <= 0.35:
            negatives.append(
                f"models differ by {spread:.0%} — moderate disagreement "
                "reduces reliability of the blended estimate"
            )
        else:
            negatives.append(
                f"models differ by {spread:.0%} — high disagreement; "
                "the blended fair value should be treated with caution"
            )

    # ── 3. Financial data source and quality ──────────────────────────────────
    fallback = stmts.get("fallback_used", False)
    source   = stmts.get("source", "")

    if fallback:
        negatives.append(
            f"financial data sourced from {source or 'a fallback provider'} "
            "(primary financial data provider was unavailable)"
        )
    elif source:
        positives.append(f"financial data from primary provider ({source.upper()})")

    completeness = inputs.get("completeness")
    if completeness is not None:
        if completeness >= 0.85:
            positives.append(f"data completeness is strong ({completeness:.0%})")
        elif completeness < 0.55:
            negatives.append(
                f"data completeness is low ({completeness:.0%}) — "
                "multiple key inputs were estimated or missing"
            )
        elif completeness < 0.75:
            negatives.append(f"data completeness is moderate ({completeness:.0%})")

    # ── 4. Sector-specific model check ────────────────────────────────────────
    if bucket in _SECTOR_CRITICAL_MODELS:
        critical_keys, label = _SECTOR_CRITICAL_MODELS[bucket]
        if not any(k in valid_models for k in critical_keys):
            negatives.append(
                f"the sector-specific {label} could not run — "
                "required financial data was unavailable"
            )

    # ── 5. DCF-specific signals ───────────────────────────────────────────────
    dcf_result = model_results.get("dcf") or {}
    if dcf_result.get("fair_value"):
        dcf_inp     = dcf_result.get("inputs_used") or {}
        terminal_pct = dcf_inp.get("terminal_pct")
        wacc         = dcf_inp.get("wacc")

        if terminal_pct and terminal_pct > 0.75:
            negatives.append(
                f"DCF terminal value represents {terminal_pct:.0%} of enterprise value — "
                "the result is highly sensitive to long-term growth assumptions"
            )
        if wacc and wacc < 0.06:
            negatives.append(
                f"DCF discount rate ({wacc:.1%} WACC) is low — "
                "may understate the cost of capital"
            )

    # ── 6. Estimation count across all warnings ───────────────────────────────
    all_warnings: list[str] = list(inputs.get("warnings") or [])
    for v in model_results.values():
        all_warnings.extend(v.get("warnings") or [])

    estimation_count = sum(
        1 for w in all_warnings
        if any(kw in w.lower() for kw in _ESTIMATION_KEYWORDS)
    )
    if estimation_count >= 5:
        negatives.append(
            f"{estimation_count} inputs were estimated or defaulted "
            "rather than directly sourced from financial statements"
        )
    elif estimation_count >= 3:
        negatives.append(
            f"{estimation_count} inputs were estimated — "
            "key assumptions may not reflect the company's actual financials"
        )

    # ── Assemble the explanation ──────────────────────────────────────────────
    if overall_confidence >= 78:
        tone = "Confidence is high"
    elif overall_confidence >= 65:
        tone = "Confidence is moderate"
    elif overall_confidence >= 50:
        tone = "Confidence is limited"
    else:
        tone = "Confidence is low"

    parts: list[str] = []

    if positives and not negatives:
        parts.append(f"{tone}: {'; '.join(positives[:3])}.")

    elif negatives and not positives:
        parts.append(f"{tone} because {'; '.join(negatives[:3])}.")

    else:
        # Mix of positive and negative — show both sides
        pos_str = "; ".join(positives[:2])
        neg_str = "; ".join(negatives[:3])
        parts.append(f"{tone}.")
        if pos_str:
            parts.append(f"Supporting factors: {pos_str}.")
        if neg_str:
            parts.append(f"Limiting factors: {neg_str}.")

    return " ".join(parts)
