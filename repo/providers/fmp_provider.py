"""
fmp_provider.py — Raw API calls to Financial Modeling Prep (FMP).

Primary source for: financial statements (income, balance sheet, cash flow),
key ratios, analyst consensus, news, and company profiles.

Updated for FMP's stable API (post Aug 2025).
All endpoints now use /stable/ base and ?symbol= query parameter instead of /{ticker} path.
"""

import requests
from datetime import datetime, timezone

from config.api_keys import FMP_API_KEY
from config.settings import FMP_BASE, REQUEST_TIMEOUT
from utils.logging_utils import get_logger, log_provider_call

log = get_logger(__name__)


def _get(endpoint: str, params: dict = None) -> dict | list:
    """
    Make a GET request to FMP stable API.
    Raises ValueError if no API key is configured.
    Raises requests.HTTPError on server error.
    """
    if not FMP_API_KEY:
        raise ValueError("FMP_API_KEY not configured")

    url = f"{FMP_BASE}{endpoint}"
    all_params = {"apikey": FMP_API_KEY, **(params or {})}

    resp = requests.get(url, params=all_params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_quote(ticker: str) -> dict:
    """
    Get a real-time quote. Returns price, change%, market cap, 52-week range.
    Note: PE and EPS are not in the stable/quote endpoint — use key-metrics or
    income statement for those.
    """
    log_provider_call(log, "FMP", f"/quote?symbol={ticker}", ticker)

    data = _get("/quote", params={"symbol": ticker})
    if not data:
        raise ValueError(f"FMP returned empty quote for {ticker}")

    q = data[0]
    change_pct = (q.get("changePercentage") or 0.0) / 100

    return {
        "ticker":     q.get("symbol", ticker).upper(),
        "name":       q.get("name"),
        "price":      q.get("price"),
        "change_pct": change_pct,
        "market_cap": q.get("marketCap"),
        "volume":     q.get("volume"),
        "year_high":  q.get("yearHigh"),
        "year_low":   q.get("yearLow"),
        "source":     "fmp",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_income_statement(ticker: str, limit: int = 4) -> list[dict]:
    """
    Get quarterly income statements, most recent first.
    Key fields: revenue, gross_profit, operating_income, net_income, ebitda, eps, shares.

    Note: gross_margin, operating_margin, net_margin are calculated here because
    the stable API no longer returns ratio fields directly.
    """
    log_provider_call(log, "FMP", f"/income-statement?symbol={ticker}", ticker)

    data = _get("/income-statement", params={"symbol": ticker, "period": "quarter", "limit": limit})
    if not data:
        raise ValueError(f"FMP returned no income statements for {ticker}")

    results = []
    for stmt in data:
        revenue          = stmt.get("revenue") or 0
        gross_profit     = stmt.get("grossProfit")
        operating_income = stmt.get("operatingIncome")
        net_income       = stmt.get("netIncome")

        results.append({
            "period":           stmt.get("period"),
            "date":             stmt.get("date"),
            "revenue":          stmt.get("revenue"),
            "gross_profit":     gross_profit,
            "operating_income": operating_income,
            "net_income":       net_income,
            "ebitda":           stmt.get("ebitda"),
            "eps":              stmt.get("eps"),
            "eps_diluted":      stmt.get("epsDiluted"),
            "shares_basic":     stmt.get("weightedAverageShsOut"),
            "shares_diluted":   stmt.get("weightedAverageShsOutDil"),
            # Calculate margins — not returned directly in stable API
            "gross_margin":     (gross_profit / revenue)     if revenue and gross_profit     is not None else None,
            "operating_margin": (operating_income / revenue) if revenue and operating_income is not None else None,
            "net_margin":       (net_income / revenue)       if revenue and net_income       is not None else None,
        })
    return results


def get_balance_sheet(ticker: str, limit: int = 4) -> list[dict]:
    """
    Get quarterly balance sheets, most recent first.
    Key fields: cash, total_debt, total_assets, total_equity, net_debt.

    Note: shares_outstanding is no longer in the stable balance sheet API.
    Use get_income_statement() shares_basic/shares_diluted instead.
    """
    log_provider_call(log, "FMP", f"/balance-sheet-statement?symbol={ticker}", ticker)

    data = _get("/balance-sheet-statement", params={"symbol": ticker, "period": "quarter", "limit": limit})
    if not data:
        raise ValueError(f"FMP returned no balance sheets for {ticker}")

    results = []
    for stmt in data:
        results.append({
            "period":            stmt.get("period"),
            "date":              stmt.get("date"),
            "cash":              stmt.get("cashAndCashEquivalents"),
            "total_assets":      stmt.get("totalAssets"),
            "total_liabilities": stmt.get("totalLiabilities"),
            "total_equity":      stmt.get("totalStockholdersEquity"),
            "total_debt":        stmt.get("totalDebt"),
            "net_debt":          stmt.get("netDebt"),
            "shares_outstanding": None,   # not available in stable API — use income stmt shares_basic
        })
    return results


def get_cash_flow_statement(ticker: str, limit: int = 4) -> list[dict]:
    """
    Get quarterly cash flow statements, most recent first.
    Key fields: operating_cash_flow, capex, free_cash_flow, depreciation.
    """
    log_provider_call(log, "FMP", f"/cash-flow-statement?symbol={ticker}", ticker)

    data = _get("/cash-flow-statement", params={"symbol": ticker, "period": "quarter", "limit": limit})
    if not data:
        raise ValueError(f"FMP returned no cash flow statements for {ticker}")

    results = []
    for stmt in data:
        results.append({
            "period":              stmt.get("period"),
            "date":                stmt.get("date"),
            "operating_cash_flow": stmt.get("operatingCashFlow"),
            "capex":               stmt.get("capitalExpenditure"),
            "free_cash_flow":      stmt.get("freeCashFlow"),
            "depreciation":        stmt.get("depreciationAndAmortization"),
            "dividends_paid":      stmt.get("netDividendsPaid"),
            "net_change_cash":     stmt.get("netChangeInCash"),
        })
    return results


def get_key_metrics(ticker: str, limit: int = 1) -> list[dict]:
    """
    Get annual key financial metrics and ratios.

    Note: the stable API only provides annual key-metrics on the standard plan.
    Quarterly period is a premium feature. Limit defaults to 1 (most recent year).

    Available: EV/EBITDA, EV/Sales, ROE, ROIC, current_ratio, working_capital.
    PE, PB, P/S, debt/equity, payout_ratio are no longer in this endpoint —
    those come from Finnhub in fundamentals_service.get_key_ratios().
    """
    log_provider_call(log, "FMP", f"/key-metrics?symbol={ticker}", ticker)

    data = _get("/key-metrics", params={"symbol": ticker, "limit": limit})
    if not data:
        raise ValueError(f"FMP returned no key metrics for {ticker}")

    results = []
    for m in data:
        results.append({
            "period":            m.get("period"),
            "date":              m.get("date"),
            "ev_ebitda":         m.get("evToEBITDA"),
            "ev_sales":          m.get("evToSales"),
            "ev_fcf":            m.get("evToFreeCashFlow"),
            "roic":              m.get("returnOnInvestedCapital"),
            "roe":               m.get("returnOnEquity"),
            "roa":               m.get("returnOnAssets"),
            "current_ratio":     m.get("currentRatio"),
            "enterprise_value":  m.get("enterpriseValue"),
            # Not available in stable standard plan — filled by Finnhub in get_key_ratios()
            "pe_ratio":          None,
            "pb_ratio":          None,
            "ps_ratio":          None,
            "debt_to_equity":    None,
            "payout_ratio":      None,
            "revenue_per_share": None,
            "fcf_per_share":     None,
        })
    return results


def get_dcf(ticker: str) -> dict:
    """
    Get FMP's own DCF intrinsic value estimate.
    Note: this is FMP's model output, not your custom DCF. Use as a reference.
    """
    log_provider_call(log, "FMP", f"/discounted-cash-flow?symbol={ticker}", ticker)

    data = _get("/discounted-cash-flow", params={"symbol": ticker})
    if not data:
        raise ValueError(f"FMP returned no DCF data for {ticker}")

    d = data[0] if isinstance(data, list) else data
    return {
        "ticker":      d.get("symbol", ticker).upper(),
        "dcf_value":   d.get("dcf"),
        "stock_price": d.get("Stock Price"),
        "source":      "fmp",
        "fetched_at":  datetime.now(timezone.utc).isoformat(),
    }


def get_stock_news(ticker: str, limit: int = 20) -> list[dict]:
    """
    Get recent news articles for a ticker from FMP.
    Used as a fallback when Finnhub returns nothing.
    """
    log_provider_call(log, "FMP", f"/news/stock?symbols={ticker}", ticker)

    data = _get("/news/stock", params={"symbols": ticker.upper(), "limit": limit})
    if not data:
        raise ValueError(f"FMP returned no news for {ticker}")

    articles = []
    for item in (data or []):
        articles.append({
            "headline":     item.get("title"),
            "summary":      item.get("text"),
            "source":       item.get("site"),
            "url":          item.get("url"),
            "published_at": item.get("publishedDate"),
            "ticker":       ticker.upper(),
            "provider":     "fmp",
        })
    return articles


def get_analyst_grades(ticker: str, limit: int = 3) -> list[dict]:
    """
    Get analyst consensus counts by month from FMP.

    Note: the stable API replaced the per-analyst historical-grade endpoint with
    monthly aggregate consensus counts. This returns the latest months' totals
    rather than individual upgrade/downgrade actions from named firms.

    Returns a list of monthly snapshots: [{"date", "buy", "hold", "sell", "total"}, ...]
    """
    log_provider_call(log, "FMP", f"/grades-historical?symbol={ticker}", ticker)

    data = _get("/grades-historical", params={"symbol": ticker, "limit": limit})
    if not data:
        raise ValueError(f"FMP returned no analyst grades for {ticker}")

    results = []
    for item in (data or []):
        buy  = (item.get("analystRatingsStrongBuy") or 0) + (item.get("analystRatingsBuy") or 0)
        hold = item.get("analystRatingsHold") or 0
        sell = (item.get("analystRatingsSell") or 0) + (item.get("analystRatingsStrongSell") or 0)
        results.append({
            "date":  item.get("date"),
            "buy":   buy,
            "hold":  hold,
            "sell":  sell,
            "total": buy + hold + sell,
        })
    return results


def get_company_profile(ticker: str) -> dict:
    """
    Get company profile: name, sector, industry, description, market cap.
    Used by the sector-aware valuation engine to choose the right models.
    """
    log_provider_call(log, "FMP", f"/profile?symbol={ticker}", ticker)

    data = _get("/profile", params={"symbol": ticker})
    if not data:
        raise ValueError(f"FMP returned no profile for {ticker}")

    p = data[0] if isinstance(data, list) else data
    return {
        "ticker":      ticker.upper(),
        "name":        p.get("companyName"),
        "sector":      p.get("sector"),
        "industry":    p.get("industry"),
        "description": p.get("description"),
        "market_cap":  p.get("marketCap"),
        "exchange":    p.get("exchange"),
        "country":     p.get("country"),
        "source":      "fmp",
    }
