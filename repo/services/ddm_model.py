"""
ddm_model.py — Dividend Discount Model (Gordon Growth Model).

Appropriate for: Consumer Staples, Utilities, Financials, Insurance, mature REITs.
Requires: consistent dividend payment and stable long-term growth outlook.

Fair Value = DPS × (1 + g) / (cost_of_equity - g)
"""

from utils.logging_utils import get_logger

log = get_logger(__name__)

# Long-run dividend growth rate assumptions by sector
_DIV_GROWTH = {
    "consumer_staples": 0.04,
    "utilities":        0.03,
    "financials":       0.05,
    "insurance":        0.04,
    "reit":             0.03,
    "industrials":      0.04,
    "communication":    0.03,
    "default":          0.04,
}


def run_ddm(ticker: str, bucket: str, ratios: dict, statements: dict, price: float) -> dict:
    """
    Gordon Growth Model DDM.

    DPS is estimated as: dividend_yield × current_price
    Cost of equity is estimated via CAPM: risk_free + beta × equity_risk_premium
    """
    warnings = []

    # ── Get dividend per share ────────────────────────────────────────────────
    div_yield = (ratios or {}).get("dividend_yield")
    if div_yield and price and div_yield > 0:
        dps = div_yield * price
    else:
        # Fallback: payout_ratio × TTM EPS
        payout = (ratios or {}).get("payout_ratio")
        income = (statements or {}).get("income") or []
        eps_ttm = sum((q.get("eps") or 0) for q in income[:4])
        if payout and eps_ttm and eps_ttm > 0:
            dps = payout * eps_ttm
            warnings.append("Dividend per share estimated from payout ratio × TTM EPS")
        else:
            return {
                "model": "ddm", "name": "Dividend Discount Model (DDM)",
                "fair_value": None, "confidence": 0.0, "inputs_used": {},
                "warnings": ["Cannot use DDM — no dividend detected or dividend data unavailable"],
            }

    if dps <= 0:
        return {
            "model": "ddm", "name": "Dividend Discount Model (DDM)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": ["Cannot use DDM — dividend per share is zero or negative"],
        }

    # ── Cost of equity (CAPM) ─────────────────────────────────────────────────
    risk_free = 0.045   # default 4.5% — US 10-year Treasury
    try:
        from services.macro_service import get_macro_snapshot
        macro = get_macro_snapshot()
        if macro and macro.get("treasury_10y"):
            rf_raw = macro["treasury_10y"].get("value")
            if rf_raw:
                risk_free = rf_raw / 100   # FRED returns as %, convert to decimal
    except Exception:
        warnings.append("Risk-free rate unavailable — defaulted to 4.5%")

    beta            = (ratios or {}).get("beta") or 1.0
    market_premium  = 0.055   # long-run US equity risk premium
    cost_of_equity  = risk_free + beta * market_premium

    div_growth = _DIV_GROWTH.get(bucket, _DIV_GROWTH["default"])

    if cost_of_equity <= div_growth:
        return {
            "model": "ddm", "name": "Dividend Discount Model (DDM)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": ["DDM invalid — cost of equity is lower than the assumed dividend growth rate"],
        }

    fair_value = dps * (1 + div_growth) / (cost_of_equity - div_growth)

    # Lower confidence if we had to estimate DPS
    confidence = 55.0 if warnings else 65.0

    return {
        "model":      "ddm",
        "name":       "Dividend Discount Model (DDM)",
        "fair_value": round(fair_value, 2),
        "confidence": confidence,
        "inputs_used": {
            "dps":            round(dps, 4),
            "div_yield":      div_yield,
            "div_growth_rate":div_growth,
            "cost_of_equity": round(cost_of_equity, 4),
            "risk_free_rate": round(risk_free, 4),
            "beta":           beta,
        },
        "warnings": warnings,
    }
