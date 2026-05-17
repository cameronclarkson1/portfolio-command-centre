"""
dcf_model.py — 3-stage Discounted Cash Flow model.

Appropriate for: Technology, Consumer, Industrials, Healthcare, Energy, Communication.
NOT appropriate for: REITs, Banks, Insurance (use sector-specific models instead).

Stage 1 (years 1-3): full estimated growth rate.
Stage 2 (years 4-5): growth fades to midpoint between Stage 1 and terminal.
Stage 3: terminal value via Gordon Growth Model.
"""

from services.fundamentals_service import get_valuation_inputs
from utils.logging_utils import get_logger

log = get_logger(__name__)

_TERMINAL_GROWTH = {
    "technology":             0.035,
    "healthcare":             0.030,
    "consumer_discretionary": 0.025,
    "consumer_staples":       0.025,
    "energy":                 0.020,
    "materials":              0.020,
    "industrials":            0.025,
    "communication":          0.025,
    "default":                0.030,
}

_MAX_GROWTH   = 0.25   # hard cap passed from fundamentals_service but enforced here too
_MAX_FV_RATIO = 5.0    # fair_value / price beyond this → confidence near zero


def run_dcf(ticker: str, bucket: str, inputs: dict | None = None, price: float = 0) -> dict:
    """
    Run a 3-stage DCF model.

    Args:
        ticker:  Stock ticker
        bucket:  Valuation bucket (used for terminal growth rate selection)
        inputs:  Pre-fetched valuation inputs dict. If None, fetches fresh data.
        price:   Current market price (used for sanity check only).

    Returns a result dict with fair_value, confidence, inputs_used, warnings.
    """
    if inputs is None:
        inputs = get_valuation_inputs(ticker)

    warnings = list(inputs.get("warnings", []))

    if not inputs.get("free_cash_flow") or not inputs.get("shares_out"):
        return {
            "model":       "dcf",
            "name":        "Discounted Cash Flow (3-stage)",
            "fair_value":  None,
            "confidence":  0.0,
            "inputs_used": {},
            "warnings":    warnings + ["DCF cannot run — free cash flow or share count missing"],
        }

    fcf        = inputs["free_cash_flow"]
    growth_raw = inputs.get("revenue_growth")
    wacc       = inputs.get("wacc_estimate", 0.09)
    terminal_g = _TERMINAL_GROWTH.get(bucket, _TERMINAL_GROWTH["default"])
    net_debt   = inputs.get("net_debt", 0) or 0
    shares_out = inputs["shares_out"]

    if growth_raw is None:
        warnings.append("Revenue growth unavailable — defaulted to 8% for DCF projection")
        growth_raw = 0.08

    # Safety cap (fundamentals_service also caps, but guard here too)
    growth_rate = min(growth_raw, _MAX_GROWTH)
    if growth_rate < growth_raw:
        warnings.append(
            f"DCF growth capped at {_MAX_GROWTH:.0%} (input was {growth_raw:.1%})"
        )

    # Fading growth: years 1-3 at full rate, years 4-5 halfway to terminal
    mid_growth  = (growth_rate + terminal_g) / 2
    stage_rates = [growth_rate, growth_rate, growth_rate, mid_growth, mid_growth]

    # Stage 1 & 2: discounted FCF projections
    pv_fcfs = []
    projected_fcf = fcf
    for year, yr_growth in enumerate(stage_rates, start=1):
        projected_fcf *= (1 + yr_growth)
        pv_fcfs.append(projected_fcf / ((1 + wacc) ** year))

    # Stage 3: terminal value
    if wacc <= terminal_g:
        warnings.append("WACC ≤ terminal growth rate — terminal value set to 0")
        pv_terminal = 0.0
    else:
        terminal_fcf   = projected_fcf * (1 + terminal_g)
        terminal_value = terminal_fcf / (wacc - terminal_g)
        pv_terminal    = terminal_value / ((1 + wacc) ** 5)

    enterprise_value = sum(pv_fcfs) + pv_terminal
    equity_value     = enterprise_value - net_debt
    fair_value       = equity_value / shares_out if shares_out else None

    # ── Sanity checks ─────────────────────────────────────────────────────────
    confidence = max(20.0, 85.0 - len([
        w for w in warnings if any(
            kw in w.lower()
            for kw in ("defaulted", "missing", "unavailable", "estimated", "cannot", "capped")
        )
    ]) * 5.0)
    confidence = round(confidence * inputs.get("completeness", 0.8), 1)

    terminal_pct = pv_terminal / enterprise_value if enterprise_value and enterprise_value > 0 else 0
    if terminal_pct > 0.80:
        warnings.append(
            f"Terminal value is {terminal_pct:.0%} of enterprise value — "
            "result is highly sensitive to WACC and terminal growth assumptions"
        )
        confidence = min(confidence, 40.0)

    if fair_value and price and price > 0:
        ratio = fair_value / price
        if ratio > _MAX_FV_RATIO:
            warnings.append(
                f"DCF fair value ({fair_value:,.0f}) is {ratio:.1f}× the market price ({price:.2f}) — "
                "likely caused by inflated growth assumptions; treat as unreliable"
            )
            confidence = min(confidence, 15.0)
        elif ratio < (1 / _MAX_FV_RATIO):
            warnings.append(
                f"DCF fair value ({fair_value:,.0f}) is only {ratio:.2f}× the market price ({price:.2f}) — "
                "result may reflect deeply negative FCF; treat with caution"
            )
            confidence = min(confidence, 25.0)

    return {
        "model":      "dcf",
        "name":       "Discounted Cash Flow (3-stage)",
        "fair_value": round(fair_value, 2) if fair_value else None,
        "confidence": confidence,
        "inputs_used": {
            "fcf_ttm":         round(fcf, 0),
            "growth_stage1":   round(growth_rate, 4),
            "growth_stage2":   round(mid_growth, 4),
            "terminal_growth": terminal_g,
            "wacc":            round(wacc, 4),
            "net_debt":        net_debt,
            "shares_out":      shares_out,
            "pv_stage1_2":     round(sum(pv_fcfs), 0),
            "pv_terminal":     round(pv_terminal, 0),
            "terminal_pct":    round(terminal_pct, 3),
        },
        "warnings": warnings,
    }
