"""
dcf_model.py — 3-stage, 10-year Discounted Cash Flow model.

Stage 1 (years 1-2):  Analyst consensus forward revenue growth.
Stage 2 (years 3-5):  Fade from analyst estimates toward long-run sustainable growth.
Stage 3 (years 6-10): Linear fade from sustainable growth to sector terminal rate.
Terminal value:        Gordon Growth Model applied at year 10.

FCF projection method: FCF margin × projected revenue.
  - FCF margin = TTM free cash flow / TTM revenue (normalises lumpy capex cycles).
  - If margin is negative or implausible, falls back to growing raw FCF directly.
"""

from services.fundamentals_service import get_valuation_inputs
from utils.logging_utils import get_logger

log = get_logger(__name__)


# ── Sector terminal growth rates ──────────────────────────────────────────────
_TERMINAL_GROWTH: dict[str, float] = {
    "technology":             0.035,
    "healthcare":             0.030,
    "consumer_discretionary": 0.025,
    "consumer_staples":       0.025,
    "energy":                 0.020,
    "materials":              0.020,
    "industrials":            0.025,
    "communication":          0.025,
    "reit":                   0.025,
    "financials":             0.025,
    "default":                0.030,
}

_MAX_GROWTH   = 0.30    # hard cap on any single projection year
_MAX_FV_RATIO = 5.0     # confidence penalty trigger vs current price


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def run_dcf(ticker: str, bucket: str, inputs: dict | None = None, price: float = 0) -> dict:
    """
    Run a 3-stage, 10-year DCF anchored to analyst consensus revenue estimates.

    Args:
        ticker:  Stock ticker
        bucket:  Valuation bucket (drives terminal growth rate selection)
        inputs:  Pre-fetched valuation inputs dict. If None, fetches fresh data.
        price:   Current market price (used for sanity checks and FCF margin method).

    Returns a result dict with fair_value, confidence, inputs_used, warnings.
    """
    if inputs is None:
        inputs = get_valuation_inputs(ticker)

    warnings = list(inputs.get("warnings", []))

    fcf        = inputs.get("free_cash_flow")
    shares_out = inputs.get("shares_out")

    if not fcf or not shares_out:
        return {
            "model":       "dcf",
            "name":        "Discounted Cash Flow (3-stage, 10-year)",
            "fair_value":  None,
            "confidence":  0.0,
            "inputs_used": {},
            "warnings":    warnings + ["DCF cannot run — free cash flow or share count missing"],
        }

    wacc        = inputs.get("wacc_estimate", 0.09)
    terminal_g  = _TERMINAL_GROWTH.get(bucket, _TERMINAL_GROWTH["default"])
    net_debt    = inputs.get("net_debt", 0) or 0
    revenue_ttm = inputs.get("revenue_ttm")

    # ── FCF margin method ─────────────────────────────────────────────────────
    # Project FCF = FCF margin × projected revenue, which is more stable than
    # compounding raw FCF (a single bad capex year would distort 10 years).
    # Accepted range: 1% – 60% (outside this → direct FCF growth fallback).
    use_margin_method = False
    fcf_margin        = None
    if revenue_ttm and revenue_ttm > 0 and fcf > 0:
        fcf_margin = fcf / revenue_ttm
        if 0.01 <= fcf_margin <= 0.60:
            use_margin_method = True

    if not use_margin_method:
        warnings.append("FCF margin method unavailable — projecting FCF directly")

    # ── Growth rate inputs ────────────────────────────────────────────────────
    analyst_y1    = inputs.get("analyst_rev_growth_y1")
    analyst_y2    = inputs.get("analyst_rev_growth_y2")
    hist_growth   = inputs.get("revenue_growth")
    analyst_count = inputs.get("analyst_count", 0) or 0

    # Sustainable growth = blend of company history and mean-reversion to 8%.
    # This is what Stage 2 converges toward before the terminal fade.
    _MEAN_REVERSION_TARGET = 0.08
    if hist_growth is not None:
        sustainable_g = _clamp(
            hist_growth * 0.5 + _MEAN_REVERSION_TARGET * 0.5,
            0.02, 0.18,
        )
    else:
        sustainable_g = _MEAN_REVERSION_TARGET

    # ── Stage 1 (Y1-2): Analyst consensus ────────────────────────────────────
    if analyst_y1 is not None:
        g_y1 = _clamp(analyst_y1, -0.30, _MAX_GROWTH)
        growth_source = f"analyst consensus ({analyst_count} analysts)"
    else:
        g_y1 = _clamp(hist_growth or _MEAN_REVERSION_TARGET, -0.30, _MAX_GROWTH)
        growth_source = "historical TTM (no analyst estimates available)"
        warnings.append("Analyst estimates unavailable — Stage 1 growth uses historical TTM rate")

    if analyst_y2 is not None:
        g_y2 = _clamp(analyst_y2, -0.30, _MAX_GROWTH)
    else:
        # Y2 naturally fades slightly from Y1 toward sustainable
        g_y2 = _clamp(g_y1 * 0.80 + sustainable_g * 0.20, -0.30, _MAX_GROWTH)

    # ── Stage 2 (Y3-5): Mean-reversion from analyst to sustainable ────────────
    g_y3 = _clamp(g_y2 * 0.60 + sustainable_g * 0.40, -0.20, _MAX_GROWTH)
    g_y4 = _clamp(g_y2 * 0.30 + sustainable_g * 0.70, -0.10, _MAX_GROWTH)
    g_y5 = _clamp(g_y2 * 0.10 + sustainable_g * 0.90, terminal_g, _MAX_GROWTH)

    # ── Stage 3 (Y6-10): Linear fade from sustainable to terminal ─────────────
    stage3_rates = [
        _clamp(sustainable_g * (1 - i / 4) + terminal_g * (i / 4), terminal_g, _MAX_GROWTH)
        for i in range(5)
    ]

    all_rates = [g_y1, g_y2, g_y3, g_y4, g_y5] + stage3_rates   # 10 years total

    # ── Project FCF and discount back ────────────────────────────────────────
    pv_fcfs = []
    if use_margin_method:
        projected_revenue = revenue_ttm
        for year, yr_growth in enumerate(all_rates, start=1):
            projected_revenue *= (1 + yr_growth)
            pv_fcfs.append(projected_revenue * fcf_margin / ((1 + wacc) ** year))
        terminal_fcf_base = projected_revenue * fcf_margin
    else:
        projected_fcf = fcf
        for year, yr_growth in enumerate(all_rates, start=1):
            projected_fcf *= (1 + yr_growth)
            pv_fcfs.append(projected_fcf / ((1 + wacc) ** year))
        terminal_fcf_base = projected_fcf

    # ── Terminal value (Gordon Growth Model at year 10) ───────────────────────
    if wacc <= terminal_g:
        warnings.append("WACC ≤ terminal growth rate — terminal value set to 0")
        pv_terminal = 0.0
    else:
        pv_terminal = (
            terminal_fcf_base * (1 + terminal_g)
            / (wacc - terminal_g)
            / ((1 + wacc) ** 10)
        )

    enterprise_value = sum(pv_fcfs) + pv_terminal
    equity_value     = enterprise_value - net_debt
    fair_value       = equity_value / shares_out if shares_out else None
    terminal_pct     = pv_terminal / enterprise_value if enterprise_value and enterprise_value > 0 else 0

    # ── Confidence scoring ────────────────────────────────────────────────────
    confidence = 70.0

    if analyst_count >= 10:
        confidence += 10.0
    elif analyst_count >= 5:
        confidence += 5.0
    elif analyst_y1 is None:
        confidence -= 15.0   # no forward anchor — penalise meaningfully

    spread = inputs.get("analyst_estimate_spread")
    if spread and spread > 0.30:
        confidence -= 10.0
        warnings.append(
            f"Analyst revenue estimate spread is {spread:.0%} — "
            "significant disagreement among analysts"
        )
    elif spread and spread > 0.15:
        confidence -= 5.0

    if terminal_pct > 0.70:
        warnings.append(
            f"Terminal value is {terminal_pct:.0%} of enterprise value — "
            "result is highly sensitive to WACC and terminal growth assumptions"
        )
        confidence -= 10.0

    for w in warnings:
        if any(kw in w.lower() for kw in ("missing", "unavailable", "defaulted", "cannot", "capped")):
            confidence -= 5.0

    confidence = round(_clamp(confidence * inputs.get("completeness", 0.85), 20.0, 85.0), 1)

    # Sanity check: flag extreme divergence from market price
    if fair_value and price and price > 0:
        ratio = fair_value / price
        if ratio > _MAX_FV_RATIO:
            warnings.append(
                f"DCF fair value (${fair_value:,.0f}) is {ratio:.1f}× market price (${price:.2f}) — "
                "likely inflated growth assumptions; treat as unreliable"
            )
            confidence = min(confidence, 15.0)
        elif ratio < (1 / _MAX_FV_RATIO):
            warnings.append(
                f"DCF fair value (${fair_value:,.0f}) is {ratio:.2f}× market price (${price:.2f}) — "
                "likely reflects deeply negative FCF; treat with caution"
            )
            confidence = min(confidence, 25.0)

    return {
        "model":      "dcf",
        "name":       "Discounted Cash Flow (3-stage, 10-year)",
        "fair_value": round(fair_value, 2) if fair_value else None,
        "confidence": confidence,
        "inputs_used": {
            "fcf_ttm":         round(fcf, 0),
            "fcf_margin":      round(fcf_margin, 4)   if fcf_margin   else None,
            "revenue_ttm":     round(revenue_ttm, 0)  if revenue_ttm  else None,
            "growth_source":   growth_source,
            "analyst_count":   analyst_count,
            "g_y1":            round(g_y1, 4),
            "g_y2":            round(g_y2, 4),
            "g_y3_y5_avg":     round((g_y3 + g_y4 + g_y5) / 3, 4),
            "g_y6_y10_avg":    round(sum(stage3_rates) / 5, 4),
            "terminal_growth": terminal_g,
            "wacc":            round(wacc, 4),
            "net_debt":        net_debt,
            "shares_out":      shares_out,
            "pv_years_1_2":    round(sum(pv_fcfs[:2]), 0),
            "pv_years_3_10":   round(sum(pv_fcfs[2:]), 0),
            "pv_terminal":     round(pv_terminal, 0),
            "terminal_pct":    round(terminal_pct, 3),
        },
        "warnings": warnings,
    }
