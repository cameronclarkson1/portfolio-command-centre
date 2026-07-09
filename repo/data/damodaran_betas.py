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
