"""
reit_valuation.py — REIT-specific valuation models.

Models:
  P/FFO  — Price to Funds From Operations (industry standard)
  P/AFFO — Price to Adjusted FFO (removes maintenance capex)

FFO = Net Income + Depreciation & Amortisation (gains on sales excluded where possible)
AFFO ≈ FFO - estimated maintenance capex (20% of total capex — rough approximation)

Share-count resolution uses a 4-step fallback chain so a missing balance-sheet
field can never silently produce a fabricated number (a wrong fair value that
looks plausible is worse than an honest N/A):

  Step 1 — balance sheet shares_outstanding      (yfinance path)
  Step 2 — income stmt shares_diluted            (FMP path)
  Step 3 — income stmt shares_basic              (FMP backup)
  Step 4 — market_cap / price derivation         (last resort; guarded)
  Fail   — explicit N/A with reason code
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


def _resolve_shares(
    statements: dict,
    ratios: dict,
    ticker: str = "",
    price: float | None = None,
) -> tuple[float | None, str]:
    """
    Resolve shares outstanding through a 4-step fallback chain.

    Returns (shares, source_label) or (None, "shares_unavailable").
    Logs the source used so every run is traceable.

    Never returns a value from a None or zero input — each step guards explicitly.
    """
    # Step 1: balance sheet shares_outstanding (yfinance path; FMP hardcodes None)
    bal    = (statements.get("balance") or [{}])[0]
    shares = bal.get("shares_outstanding")
    if shares and shares > 0:
        log.info(f"[REIT shares] {ticker}: resolved from balance_sheet ({shares:,.0f})")
        return float(shares), "balance_sheet"

    # Steps 2 & 3: income statement diluted / basic shares (FMP path)
    income = statements.get("income") or []
    for q in income[:4]:
        shares = q.get("shares_diluted") or q.get("shares_basic")
        if shares and shares > 0:
            log.info(f"[REIT shares] {ticker}: resolved from income_statement ({shares:,.0f})")
            return float(shares), "income_statement"

    # Step 4: market_cap / price derivation — last resort only
    market_cap = (ratios or {}).get("market_cap")
    if market_cap and market_cap > 0 and price and price > 0:
        shares = market_cap / price
        log.warning(
            f"[REIT shares] {ticker}: derived from market_cap/price "
            f"({market_cap:,.0f} / {price:.2f} = {shares:,.0f}) — "
            "verify against filings; this is an approximation"
        )
        return float(shares), "market_cap_price_derived"

    log.error(
        f"[REIT shares] {ticker}: all sources failed — "
        f"balance_sheet={bal.get('shares_outstanding')!r}, "
        f"income_stmt_diluted={None if not income else income[0].get('shares_diluted')!r}, "
        f"market_cap={market_cap!r}, price={price!r}"
    )
    return None, "shares_unavailable"


def run_pffo(ratios: dict, statements: dict, price: float | None = None, ticker: str = "") -> dict:
    """
    P/FFO valuation.
    FFO per share = (Net Income TTM + D&A TTM) / Shares Outstanding
    Simplified: gains on property sales are not excluded (not available from standard APIs).
    """
    net_income   = _annualise(statements, "net_income",   "income")
    depreciation = _annualise(statements, "depreciation", "cashflow")
    shares_out, shares_source = _resolve_shares(statements, ratios, ticker=ticker, price=price)

    if not net_income:
        return {
            "model": "pffo", "name": "P/FFO (Funds From Operations)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": ["P/FFO cannot run — net income unavailable (net_income=None or 0 after TTM sum)"],
        }

    if not shares_out:
        return {
            "model": "pffo", "name": "P/FFO (Funds From Operations)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": [
                f"P/FFO cannot run — shares_unavailable after all fallback sources exhausted "
                f"(balance_sheet=None, income_stmt=None, market_cap/price derivation also failed)"
            ],
        }

    ffo           = net_income + (depreciation or 0)
    ffo_per_share = ffo / shares_out

    if ffo_per_share <= 0:
        return {
            "model": "pffo", "name": "P/FFO (Funds From Operations)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": [f"P/FFO cannot run — FFO per share is negative ({ffo_per_share:.2f})"],
        }

    warnings = [
        "FFO simplified as Net Income + D&A. Gains on property sales not excluded "
        "(unavailable from standard financial APIs) — actual FFO may differ."
    ]
    if shares_source == "income_statement":
        warnings.append("Share count from income statement (weighted-average diluted) — balance sheet shares unavailable from FMP stable API")
    elif shares_source == "market_cap_price_derived":
        warnings.append("Share count DERIVED from market_cap/price — treat P/FFO fair value with caution; verify share count against filings")

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
            "shares_source":      shares_source,
        },
        "warnings": warnings,
    }


def run_paffo(ratios: dict, statements: dict, price: float | None = None, ticker: str = "") -> dict:
    """
    P/AFFO valuation.
    AFFO ≈ FFO - Maintenance Capex
    Maintenance capex estimated as 20% of total capex (industry rule of thumb).
    """
    net_income   = _annualise(statements, "net_income",   "income")
    depreciation = _annualise(statements, "depreciation", "cashflow")
    capex        = _annualise(statements, "capex",        "cashflow")
    shares_out, shares_source = _resolve_shares(statements, ratios, ticker=ticker, price=price)

    if not net_income:
        return {
            "model": "paffo", "name": "P/AFFO (Adjusted Funds From Operations)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": ["P/AFFO cannot run — net income unavailable (net_income=None or 0 after TTM sum)"],
        }

    if not shares_out:
        return {
            "model": "paffo", "name": "P/AFFO (Adjusted Funds From Operations)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": [
                "P/AFFO cannot run — shares_unavailable after all fallback sources exhausted "
                "(balance_sheet=None, income_stmt=None, market_cap/price derivation also failed)"
            ],
        }

    ffo               = net_income + (depreciation or 0)
    maintenance_capex = abs(capex or 0) * 0.20
    affo              = ffo - maintenance_capex
    affo_per_share    = affo / shares_out

    if affo_per_share <= 0:
        return {
            "model": "paffo", "name": "P/AFFO (Adjusted Funds From Operations)",
            "fair_value": None, "confidence": 0.0, "inputs_used": {},
            "warnings": [f"P/AFFO cannot run — AFFO per share is negative ({affo_per_share:.2f}) after capex adjustment"],
        }

    warnings = [
        "Maintenance capex estimated at 20% of total capex — actual AFFO may differ. "
        "For precise AFFO, refer to the company's own supplemental filings."
    ]
    if shares_source == "income_statement":
        warnings.append("Share count from income statement (weighted-average diluted) — balance sheet shares unavailable from FMP stable API")
    elif shares_source == "market_cap_price_derived":
        warnings.append("Share count DERIVED from market_cap/price — treat P/AFFO fair value with caution; verify share count against filings")

    return {
        "model":      "paffo",
        "name":       "P/AFFO (Adjusted Funds From Operations)",
        "fair_value": round(affo_per_share * PAFFO_BENCHMARK, 2),
        "confidence": 55.0,
        "inputs_used": {
            "ffo_ttm":                round(ffo, 0),
            "maintenance_capex_est":  round(maintenance_capex, 0),
            "affo_ttm":               round(affo, 0),
            "affo_per_share":         round(affo_per_share, 2),
            "paffo_benchmark":        PAFFO_BENCHMARK,
            "shares_source":          shares_source,
        },
        "warnings": warnings,
    }
