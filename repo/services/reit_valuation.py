"""
reit_valuation.py — REIT-specific valuation models.

Models:
  P/FFO  — Price to Funds From Operations (industry standard)
  P/AFFO — Price to Adjusted FFO (removes maintenance capex)

FFO = Net Income + Depreciation & Amortisation (gains on sales excluded where possible)
AFFO ≈ FFO - estimated maintenance capex (20% of total capex — rough approximation)
"""

from utils.logging_utils import get_logger

log = get_logger(__name__)

PFFO_BENCHMARK  = 18.0   # S&P Equity REIT index approximate P/FFO (2024-2025)
PAFFO_BENCHMARK = 22.0   # REITs typically trade at higher P/AFFO (AFFO < FFO)


def _annualise(statements: dict, field: str, statement_type: str) -> float | None:
    """Sum the last 4 quarters of a field to get a TTM annual figure."""
    data = statements.get(statement_type) or []
    total = sum((q.get(field) or 0) for q in data[:4])
    return total if total != 0 else None


def run_pffo(ratios: dict, statements: dict) -> dict:
    """
    P/FFO valuation.
    FFO per share = (Net Income TTM + D&A TTM) / Shares Outstanding
    Simplified: gains on property sales are not excluded (not available from standard APIs).
    """
    net_income   = _annualise(statements, "net_income",   "income")
    depreciation = _annualise(statements, "depreciation", "cashflow")
    bal          = (statements.get("balance") or [{}])[0]
    shares_out   = bal.get("shares_outstanding")

    if not net_income or not shares_out:
        return {
            "model": "pffo", "name": "P/FFO (Funds From Operations)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": ["P/FFO cannot run — net income or share count missing"],
        }

    ffo           = net_income + (depreciation or 0)
    ffo_per_share = ffo / shares_out

    if ffo_per_share <= 0:
        return {
            "model": "pffo", "name": "P/FFO (Funds From Operations)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": ["P/FFO cannot run — FFO per share is negative"],
        }

    return {
        "model":      "pffo",
        "name":       "P/FFO (Funds From Operations)",
        "fair_value": round(ffo_per_share * PFFO_BENCHMARK, 2),
        "confidence": 65.0,
        "inputs_used": {
            "net_income_ttm":     round(net_income, 0),
            "depreciation_ttm":   round(depreciation or 0, 0),
            "ffo_ttm":            round(ffo, 0),
            "ffo_per_share":      round(ffo_per_share, 2),
            "pffo_benchmark":     PFFO_BENCHMARK,
        },
        "warnings": [
            "FFO simplified as Net Income + D&A. Gains on property sales not excluded "
            "(unavailable from standard financial APIs) — actual FFO may differ."
        ],
    }


def run_paffo(ratios: dict, statements: dict) -> dict:
    """
    P/AFFO valuation.
    AFFO ≈ FFO - Maintenance Capex
    Maintenance capex estimated as 20% of total capex (industry rule of thumb).
    """
    net_income   = _annualise(statements, "net_income",   "income")
    depreciation = _annualise(statements, "depreciation", "cashflow")
    capex        = _annualise(statements, "capex",        "cashflow")
    bal          = (statements.get("balance") or [{}])[0]
    shares_out   = bal.get("shares_outstanding")

    if not net_income or not shares_out:
        return {
            "model": "paffo", "name": "P/AFFO (Adjusted Funds From Operations)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": ["P/AFFO cannot run — net income or share count missing"],
        }

    ffo               = net_income + (depreciation or 0)
    maintenance_capex = abs(capex or 0) * 0.20   # 20% of total capex = maintenance estimate
    affo              = ffo - maintenance_capex
    affo_per_share    = affo / shares_out

    if affo_per_share <= 0:
        return {
            "model": "paffo", "name": "P/AFFO (Adjusted Funds From Operations)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": ["P/AFFO cannot run — AFFO per share is negative after capex adjustment"],
        }

    return {
        "model":      "paffo",
        "name":       "P/AFFO (Adjusted Funds From Operations)",
        "fair_value": round(affo_per_share * PAFFO_BENCHMARK, 2),
        "confidence": 55.0,   # lower — maintenance capex estimate is rough
        "inputs_used": {
            "ffo_ttm":                round(ffo, 0),
            "maintenance_capex_est":  round(maintenance_capex, 0),
            "affo_ttm":               round(affo, 0),
            "affo_per_share":         round(affo_per_share, 2),
            "paffo_benchmark":        PAFFO_BENCHMARK,
        },
        "warnings": [
            "Maintenance capex estimated at 20% of total capex — actual AFFO may differ. "
            "For precise AFFO, refer to the company's own supplemental filings."
        ],
    }
