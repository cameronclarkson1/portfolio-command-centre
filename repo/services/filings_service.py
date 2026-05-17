"""
filings_service.py — SEC filing retrieval and revenue validation.

Functions:
  get_sec_filings(ticker, form_type)          → list of recent filings with links
  validate_financials_against_sec(ticker)     → cross-check FMP revenue vs SEC EDGAR
"""

import providers.sec_edgar_provider as sec_edgar
import providers.fmp_provider       as fmp

from services import _try_providers
from storage.cache_manager import cache
from config.settings import CACHE_TTL
from utils.logging_utils import get_logger, log_cache_hit, log_cache_miss
from utils.validation_utils import cross_validate

log = get_logger(__name__)


def get_sec_filings(ticker: str, form_type: str = "10-K", count: int = 5) -> list[dict]:
    """
    Return a list of recent SEC filings for a ticker.

    Each item:
    {
        "ticker":           "MSFT",
        "form_type":        "10-K",
        "filed_date":       "2024-07-30",
        "accession_number": "0000950170-24-087843",
        "filing_url":       "https://www.sec.gov/Archives/...",
        "source":           "sec_edgar",
    }

    Args:
        form_type: "10-K" (annual), "10-Q" (quarterly), "8-K" (events)
        count:     Maximum number of filings to return
    """
    ticker    = ticker.upper()
    cache_key = f"filings:{ticker}:{form_type}"
    ttl       = CACHE_TTL["sec_filing"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    result, _, _ = _try_providers([
        ("sec_edgar", lambda: sec_edgar.get_recent_filings(ticker, form_type, count)),
    ], f"{ticker} SEC {form_type} filings")

    filings = result or []

    if filings:
        cache.set(cache_key, filings, ttl)

    return filings


def validate_financials_against_sec(ticker: str) -> dict:
    """
    Cross-check revenue figures from FMP against SEC EDGAR official filings.

    This is the data quality check: if FMP says revenue is $50B but SEC says $45B,
    we flag it as a discrepancy and reduce confidence in the fundamentals data.

    Returns:
    {
        "ticker":         "MSFT",
        "validation_run": True,
        "years_checked":  3,
        "agreements":     3,        # years where FMP and SEC agreed within 5%
        "discrepancies":  0,        # years where they disagreed
        "agreement_rate": 1.0,      # 0.0 to 1.0
        "sec_revenue_history": [...],
        "fmp_revenue_history": [...],
        "warnings":       [],
        "confidence_adjustment": +5,  # bonus to fundamentals confidence if sources agree
    }
    """
    ticker    = ticker.upper()
    cache_key = f"sec_validation:{ticker}"
    ttl       = CACHE_TTL["sec_filing"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    warnings = []
    result   = {
        "ticker":          ticker,
        "validation_run":  False,
        "years_checked":   0,
        "agreements":      0,
        "discrepancies":   0,
        "agreement_rate":  None,
        "warnings":        [],
        "confidence_adjustment": 0,
    }

    # Get SEC revenue history
    sec_revenues = []
    try:
        sec_revenues = sec_edgar.get_revenue_history(ticker)
    except Exception as e:
        warnings.append(f"SEC EDGAR revenue lookup failed: {e}")

    # Get FMP revenue history from income statements
    fmp_revenues = []
    try:
        fmp_stmts = fmp.get_income_statement(ticker, limit=8)
        # Aggregate quarterly data by year
        by_year = {}
        for stmt in fmp_stmts:
            year = (stmt.get("date") or "")[:4]
            if year:
                by_year[year] = by_year.get(year, 0) + (stmt.get("revenue") or 0)
        fmp_revenues = [{"year": yr, "value": val} for yr, val in by_year.items()]
        fmp_revenues.sort(key=lambda x: x["year"], reverse=True)
    except Exception as e:
        warnings.append(f"FMP revenue lookup failed: {e}")

    if not sec_revenues or not fmp_revenues:
        result["warnings"] = warnings + ["Cannot validate — one or both sources unavailable"]
        return result

    # Compare year by year
    sec_by_year = {r["year"]: r["value"] for r in sec_revenues}
    fmp_by_year = {r["year"]: r["value"] for r in fmp_revenues}
    common_years = sorted(set(sec_by_year) & set(fmp_by_year), reverse=True)[:5]

    agreements    = 0
    discrepancies = 0
    for year in common_years:
        sec_val = sec_by_year[year]
        fmp_val = fmp_by_year[year]
        if cross_validate(sec_val, fmp_val, tolerance=0.05):
            agreements += 1
        else:
            discrepancies += 1
            diff_pct = abs(sec_val - fmp_val) / max(abs(sec_val), 1) * 100
            warnings.append(
                f"{year}: FMP revenue ${fmp_val/1e9:.1f}B vs SEC ${sec_val/1e9:.1f}B "
                f"({diff_pct:.1f}% difference — use SEC as source of truth)"
            )

    years_checked  = len(common_years)
    agreement_rate = agreements / years_checked if years_checked else None

    result.update({
        "validation_run":       True,
        "years_checked":        years_checked,
        "agreements":           agreements,
        "discrepancies":        discrepancies,
        "agreement_rate":       agreement_rate,
        "sec_revenue_history":  sec_revenues[:5],
        "fmp_revenue_history":  fmp_revenues[:5],
        "warnings":             warnings,
        # Reward agreement with confidence bonus, penalise discrepancies
        "confidence_adjustment": +5 if (agreement_rate or 0) >= 0.8 else -10,
    })

    cache.set(cache_key, result, ttl)
    return result
