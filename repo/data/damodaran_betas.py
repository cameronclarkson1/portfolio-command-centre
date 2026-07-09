"""
damodaran_betas.py — Sector-level unlevered betas and equity risk premium.

Source: Aswath Damodaran (NYU Stern), January 2025 dataset.
https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html

These are industry-average UNLEVERED (asset) betas for US companies.
We re-lever them at runtime using each company's actual D/E ratio.

Why use sector betas instead of the company's own beta?
  - A company's raw beta from 1-2 years of daily returns is noisy
  - It picks up short-term idiosyncratic events (earnings surprise, CEO change)
  - The sector average is more stable and reflects fundamental business risk
  - We then personalise it for the company's financial leverage

Update schedule: refresh these values each January when Damodaran publishes
the new dataset. Last updated: January 2025.
"""

# ── Equity Risk Premium ───────────────────────────────────────────────────────
# Damodaran's implied ERP for the US market as of January 2025.
# This is the excess return investors demand over the risk-free rate.
# Our previous hardcoded value was 5.5% — this is more calibrated.
DAMODARAN_ERP: float = 0.046   # 4.60%

# ── Unlevered betas by sector ─────────────────────────────────────────────────
# Keys match FMP company profile sector names exactly.
# Values are unlevered (asset) betas — debt-free business risk only.

SECTOR_UNLEVERED_BETA: dict[str, float] = {
    "Technology":              1.05,   # software + hardware blend
    "Communication Services":  0.88,
    "Healthcare":              0.78,   # pharma + devices blend
    "Consumer Discretionary":  0.93,
    "Consumer Staples":        0.62,
    "Financials":              0.52,   # banks have operating leverage, lower asset beta
    "Energy":                  0.90,
    "Utilities":               0.36,   # regulated, low risk
    "Industrials":             0.90,
    "Materials":               0.88,
    "Real Estate":             0.68,
}

_DEFAULT_UNLEVERED_BETA: float = 0.90   # conservative default when sector unknown


def get_unlevered_beta(sector: str, industry: str = "") -> float:
    """
    Return Damodaran's unlevered beta for the given sector.

    Falls back to industry-level refinements for notable sub-sectors,
    then to the sector default, then to the overall market default.

    Args:
        sector:   FMP sector string (e.g. "Technology", "Healthcare")
        industry: FMP industry string for sub-sector refinement (optional)
    """
    industry_lower = (industry or "").lower()

    # Sub-sector refinements within Technology
    if sector == "Technology":
        if "semiconductor" in industry_lower:
            return 1.18   # semiconductors carry higher cyclical risk
        if "software" in industry_lower:
            return 1.10   # pure software: high margins but growth-rate sensitive

    # Sub-sector refinements within Healthcare
    if sector == "Healthcare":
        if "biotech" in industry_lower or "biotechnology" in industry_lower:
            return 1.28   # binary trial outcomes = high risk
        if "pharmaceutical" in industry_lower or "drug" in industry_lower:
            return 0.72
        if "device" in industry_lower or "equipment" in industry_lower:
            return 0.85

    # Sub-sector refinements within Financials
    if sector == "Financials":
        if "insurance" in industry_lower:
            return 0.65
        if "asset management" in industry_lower or "investment" in industry_lower:
            return 0.78

    return SECTOR_UNLEVERED_BETA.get(sector, _DEFAULT_UNLEVERED_BETA)


# ── Synthetic credit rating (Damodaran default spread table) ─────────────────
# Coverage ratio = EBIT / Interest Expense.
# Maps to a credit rating and a default spread, which we add to the risk-free
# rate to get cost of debt. Source: Damodaran "ratings.xls", January 2025.
# Entries are (min_coverage, spread_decimal, rating_label).
# The table is sorted descending: first match wins.
_COVERAGE_TABLE: list[tuple[float, float, str]] = [
    (8.50,  0.0063, "Aaa/AAA"),
    (6.50,  0.0078, "Aa2/AA"),
    (5.50,  0.0088, "A1/A+"),
    (4.25,  0.0098, "A2/A"),
    (3.00,  0.0113, "A3/A-"),
    (2.50,  0.0138, "Baa2/BBB"),
    (2.00,  0.0163, "Ba1/BB+"),
    (1.75,  0.0213, "Ba2/BB"),
    (1.50,  0.0263, "B1/B+"),
    (1.25,  0.0338, "B2/B"),
    (0.80,  0.0438, "B3/B-"),
    (0.65,  0.0538, "Caa/CCC"),
    (0.20,  0.0688, "Ca2/CC"),
    (0.00,  0.1063, "C2/C"),
]
_DISTRESSED_SPREAD: float = 0.1463   # D-rated / negative coverage
_DISTRESSED_RATING: str   = "D"


def synthetic_default_spread(
    ebit_ttm: float | None,
    interest_expense_ttm: float | None,
) -> tuple[float, str]:
    """
    Estimate a company's default spread from its interest coverage ratio.

    Returns (spread_as_decimal, rating_label).
    E.g. (0.0138, "Baa2/BBB") means add 1.38% to the risk-free rate.

    If either input is missing, returns the Baa spread as a neutral default.
    """
    if not ebit_ttm or not interest_expense_ttm or interest_expense_ttm <= 0:
        return 0.0138, "Baa2/BBB"   # neutral default — no data to work with

    coverage = ebit_ttm / interest_expense_ttm

    if coverage <= 0:
        return _DISTRESSED_SPREAD, _DISTRESSED_RATING

    for min_cov, spread, rating in _COVERAGE_TABLE:
        if coverage >= min_cov:
            return spread, rating

    return _DISTRESSED_SPREAD, _DISTRESSED_RATING


def relevered_beta(
    unlevered: float,
    total_debt: float,
    market_equity: float,
    tax_rate: float,
) -> float:
    """
    Re-lever an unlevered beta for a company's actual capital structure.

    Formula (Hamada equation):
        levered_beta = unlevered_beta × (1 + (1 - tax_rate) × (D / E))

    Args:
        unlevered:     Sector unlevered beta from Damodaran
        total_debt:    Company's total debt (dollars)
        market_equity: Company's market capitalisation (dollars)
        tax_rate:      Effective tax rate (decimal, e.g. 0.21)

    Returns the re-levered beta. Capped at [0.10, 3.0] to prevent
    extreme values from distorting WACC on highly leveraged companies.
    """
    if market_equity <= 0:
        return unlevered   # can't lever if no equity value

    de_ratio = total_debt / market_equity
    levered  = unlevered * (1 + (1 - tax_rate) * de_ratio)
    return max(0.10, min(3.0, levered))
