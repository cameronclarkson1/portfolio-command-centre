"""
sec_edgar_provider.py — Raw API calls to SEC EDGAR.

SEC EDGAR is the official source for all US company filings.
Used as a validation layer: we compare FMP's financial figures
against the numbers reported directly in SEC filings.

Free and open — no API key needed.
SEC policy requires a User-Agent header identifying your application.
"""

import requests
from datetime import datetime, timezone

from config.api_keys import SEC_USER_AGENT
from config.settings import SEC_EDGAR_BASE, REQUEST_TIMEOUT
from utils.logging_utils import get_logger, log_provider_call

log = get_logger(__name__)

# SEC requires this header — without it, requests may be blocked
_HEADERS = {"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}

# Cache the full ticker→CIK map in memory (fetched once per session)
_TICKER_CIK_MAP: dict[str, str] = {}


def _get(url: str) -> dict | list:
    """Make a GET request to SEC EDGAR with the required User-Agent header."""
    resp = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _load_cik_map() -> dict[str, str]:
    """
    Load the full ticker → CIK mapping from SEC EDGAR.
    This is a single JSON file that maps every US public company to its CIK number.
    The result is cached in memory for the session.

    CIK is zero-padded to 10 digits, e.g. "0000789019" for Microsoft.
    """
    global _TICKER_CIK_MAP

    if _TICKER_CIK_MAP:
        return _TICKER_CIK_MAP

    log.info("SEC EDGAR: loading ticker→CIK map")
    data = _get("https://www.sec.gov/files/company_tickers.json")

    # Response format: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
    for item in data.values():
        ticker = item.get("ticker", "").upper()
        cik    = str(item.get("cik_str", "")).zfill(10)  # pad to 10 digits
        if ticker:
            _TICKER_CIK_MAP[ticker] = cik

    log.info(f"SEC EDGAR: loaded {len(_TICKER_CIK_MAP)} tickers")
    return _TICKER_CIK_MAP


def get_cik(ticker: str) -> str:
    """
    Look up the SEC CIK (Central Index Key) for a ticker symbol.
    CIK is the unique ID used in all SEC EDGAR API calls.

    Returns a 10-digit zero-padded string, e.g. "0000789019"
    Raises ValueError if the ticker is not found.
    """
    cik_map = _load_cik_map()
    cik = cik_map.get(ticker.upper())

    if not cik:
        raise ValueError(f"SEC EDGAR: no CIK found for ticker '{ticker}'")

    return cik


def get_recent_filings(ticker: str, form_type: str = "10-K", count: int = 5) -> list[dict]:
    """
    Get a list of recent SEC filings for a company.

    Args:
        ticker:    Stock ticker, e.g. "MSFT"
        form_type: Filing type: "10-K" (annual), "10-Q" (quarterly), "8-K" (events)
        count:     Maximum number of filings to return

    Returns a list of filing dicts with: form_type, filed_date, accession_number, filing_url
    """
    cik = get_cik(ticker)
    log_provider_call(log, "SEC EDGAR", f"/submissions/CIK{cik}.json", ticker)

    data = _get(f"{SEC_EDGAR_BASE}/submissions/CIK{cik}.json")

    recent = data.get("filings", {}).get("recent", {})
    forms    = recent.get("form",        [])
    dates    = recent.get("filingDate",  [])
    accnums  = recent.get("accessionNumber", [])

    filings = []
    for form, date, accnum in zip(forms, dates, accnums):
        if form == form_type:
            # Build the filing URL on EDGAR viewer
            accnum_clean = accnum.replace("-", "")
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{int(cik)}/{accnum_clean}/{accnum}-index.htm"
            )
            filings.append({
                "ticker":           ticker.upper(),
                "form_type":        form,
                "filed_date":       date,
                "accession_number": accnum,
                "filing_url":       filing_url,
                "source":           "sec_edgar",
            })
            if len(filings) >= count:
                break

    return filings


def get_company_facts(ticker: str) -> dict:
    """
    Get all XBRL financial facts for a company from SEC EDGAR.

    This is the source-of-truth for financial figures. The response is large
    (several MB) and contains every reported number in every filing.

    Key paths in the returned dict:
      facts["us-gaap"]["Revenues"]["units"]["USD"]        → revenue history
      facts["us-gaap"]["NetIncomeLoss"]["units"]["USD"]   → net income history
      facts["us-gaap"]["Assets"]["units"]["USD"]          → total assets history

    Note: Variable name matters — "Revenues" vs "RevenueFromContractWithCustomer"
    differs by company depending on which GAAP concept they use.
    """
    cik = get_cik(ticker)
    log_provider_call(log, "SEC EDGAR", f"/api/xbrl/companyfacts/CIK{cik}.json", ticker)

    data = _get(f"{SEC_EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json")
    return data.get("facts", {})


def get_revenue_history(ticker: str) -> list[dict]:
    """
    Extract just the annual revenue history from SEC EDGAR company facts.
    Used to cross-validate revenue figures reported by FMP or Finnhub.

    Returns a list of dicts: [{"year": "2024", "value": 211000000000, "form": "10-K"}, ...]
    sorted most recent first.
    """
    facts = get_company_facts(ticker)
    gaap  = facts.get("us-gaap", {})

    # Companies use different GAAP concepts for revenue — try common ones in order
    revenue_concepts = [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ]

    revenue_data = None
    for concept in revenue_concepts:
        if concept in gaap:
            revenue_data = gaap[concept].get("units", {}).get("USD", [])
            if revenue_data:
                break

    if not revenue_data:
        return []

    # Filter to annual 10-K filings only (form == "10-K", period ~12 months)
    annual = [
        {
            "year":   r.get("end", "")[:4],
            "period": r.get("end"),
            "value":  r.get("val"),
            "form":   r.get("form"),
        }
        for r in revenue_data
        if r.get("form") == "10-K" and r.get("val") is not None
    ]

    # Deduplicate by year, keep the most recently filed
    by_year = {}
    for r in annual:
        yr = r["year"]
        if yr not in by_year:
            by_year[yr] = r

    return sorted(by_year.values(), key=lambda x: x["year"], reverse=True)
