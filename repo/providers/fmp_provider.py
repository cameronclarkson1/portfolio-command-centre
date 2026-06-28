"""
fmp_provider.py — Raw API calls to Financial Modeling Prep (FMP).

Primary source for: financial statements (income, balance sheet, cash flow),
key ratios, analyst estimates, valuation inputs, and DCF estimates.

Free tier: 250 requests/day.
"""

import requests
from datetime import datetime, timezone

from config.api_keys import FMP_API_KEY
from config.settings import FMP_BASE, REQUEST_TIMEOUT
from utils.logging_utils import get_logger, log_provider_call

log = get_logger(__name__)


def _get(endpoint: str, params: dict = None) -> dict | list:
    """
    Make a GET request to FMP.
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
    Get a detailed real-time quote including fundamentals summary.
    Returns: price, change%, market cap, P/E, EPS, 52-week range, volume.
    """
    log_provider_call(log, "FMP", f"/quote/{ticker}", ticker)

    data = _get(f"/quote/{ticker}")
    if not data:
        raise ValueError(f"FMP returned empty quote for {ticker}")

    q = data[0]  # FMP returns a list with one item
    change_pct = (q.get("changesPercentage") or 0.0) / 100

    return {
        "ticker":        q.get("symbol", ticker).upper(),
        "name":          q.get("name"),
        "price":         q.get("price"),
        "change_pct":    change_pct,
        "market_cap":    q.get("marketCap"),
        "pe_ratio":      q.get("pe"),
        "eps":           q.get("eps"),
        "volume":        q.get("volume"),
        "avg_volume":    q.get("avgVolume"),
        "year_high":     q.get("yearHigh"),
        "year_low":      q.get("yearLow"),
        "shares_out":    q.get("sharesOutstanding"),
        "source":        "fmp",
        "fetched_at":    datetime.now(timezone.utc).isoformat(),
    }


def get_income_statement(ticker: str, limit: int = 4) -> list[dict]:
    """
    Get quarterly income statements.
    Returns up to `limit` quarters, most recent first.

    Key fields: revenue, gross_profit, operating_income, net_income, ebitda, eps.
    """
    log_provider_call(log, "FMP", f"/income-statement/{ticker}", ticker)

    data = _get(f"/income-statement/{ticker}", params={"period": "quarter", "limit": limit})
    if not data:
        raise ValueError(f"FMP returned no income statements for {ticker}")

    results = []
    for stmt in data:
        results.append({
            "period":           stmt.get("period"),
            "date":             stmt.get("date"),
            "revenue":          stmt.get("revenue"),
            "gross_profit":     stmt.get("grossProfit"),
            "operating_income": stmt.get("operatingIncome"),
            "net_income":       stmt.get("netIncome"),
            "ebitda":           stmt.get("ebitda"),
            "eps":              stmt.get("eps"),
            "eps_diluted":      stmt.get("epsdiluted"),
            "gross_margin":     stmt.get("grossProfitRatio"),
            "operating_margin": stmt.get("operatingIncomeRatio"),
            "net_margin":       stmt.get("netIncomeRatio"),
        })
    return results


def get_balance_sheet(ticker: str, limit: int = 4) -> list[dict]:
    """
    Get quarterly balance sheets.
    Key fields: cash, total_debt, total_assets, total_equity, shares_outstanding.
    """
    log_provider_call(log, "FMP", f"/balance-sheet-statement/{ticker}", ticker)

    data = _get(f"/balance-sheet-statement/{ticker}", params={"period": "quarter", "limit": limit})
    if not data:
        raise ValueError(f"FMP returned no balance sheets for {ticker}")

    results = []
    for stmt in data:
        results.append({
            "period":               stmt.get("period"),
            "date":                 stmt.get("date"),
            "cash":                 stmt.get("cashAndCashEquivalents"),
            "total_assets":         stmt.get("totalAssets"),
            "total_liabilities":    stmt.get("totalLiabilities"),
            "total_equity":         stmt.get("totalStockholdersEquity"),
            "total_debt":           stmt.get("totalDebt"),
            "net_debt":             stmt.get("netDebt"),
            "shares_outstanding":   stmt.get("commonStockSharesOutstanding") or stmt.get("commonStock"),
        })
    return results


def get_cash_flow_statement(ticker: str, limit: int = 4) -> list[dict]:
    """
    Get quarterly cash flow statements.
    Key fields: operating_cash_flow, capex, free_cash_flow, dividends_paid.
    """
    log_provider_call(log, "FMP", f"/cash-flow-statement/{ticker}", ticker)

    data = _get(f"/cash-flow-statement/{ticker}", params={"period": "quarter", "limit": limit})
    if not data:
        raise ValueError(f"FMP returned no cash flow statements for {ticker}")

    results = []
    for stmt in data:
        results.append({
            "period":               stmt.get("period"),
            "date":                 stmt.get("date"),
            "operating_cash_flow":  stmt.get("operatingCashFlow"),
            "capex":                stmt.get("capitalExpenditure"),
            "free_cash_flow":       stmt.get("freeCashFlow"),
            "depreciation":         stmt.get("depreciationAndAmortization"),
            "dividends_paid":       stmt.get("dividendsPaid"),
            "net_change_cash":      stmt.get("netChangeInCash"),
        })
    return results


def get_key_metrics(ticker: str, limit: int = 4) -> list[dict]:
    """
    Get key financial metrics and ratios per quarter.
    Includes: EV/EBITDA, P/FCF, ROIC, debt/equity, and more.
    """
    log_provider_call(log, "FMP", f"/key-metrics/{ticker}", ticker)

    data = _get(f"/key-metrics/{ticker}", params={"period": "quarter", "limit": limit})
    if not data:
        raise ValueError(f"FMP returned no key metrics for {ticker}")

    results = []
    for m in data:
        results.append({
            "period":           m.get("period"),
            "date":             m.get("date"),
            "revenue_per_share": m.get("revenuePerShare"),
            "fcf_per_share":    m.get("freeCashFlowPerShare"),
            "roic":             m.get("roic"),
            "roe":              m.get("roe"),
            "ev_ebitda":        m.get("enterpriseValueOverEBITDA"),
            "pe_ratio":         m.get("peRatio"),
            "pb_ratio":         m.get("pbRatio"),
            "ps_ratio":         m.get("priceToSalesRatio"),
            "debt_to_equity":   m.get("debtToEquity"),
            "current_ratio":    m.get("currentRatio"),
            "payout_ratio":     m.get("payoutRatio"),
        })
    return results


def get_dcf(ticker: str) -> dict:
    """
    Get FMP's own DCF intrinsic value estimate.
    Note: this is FMP's model output, not your custom DCF. Use as a reference.
    """
    log_provider_call(log, "FMP", f"/discounted-cash-flow/{ticker}", ticker)

    data = _get(f"/discounted-cash-flow/{ticker}")
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

    Returns a list of article dicts with: headline, summary, source, url, published_at.
    """
    log_provider_call(log, "FMP", f"/stock_news?tickers={ticker}", ticker)

    data = _get("/stock_news", params={"tickers": ticker.upper(), "limit": limit})
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


# Map FMP's short action codes to readable labels
_GRADE_ACTION_LABELS = {
    "up":   "Upgrade",
    "down": "Downgrade",
    "init": "Initiate",
    "main": "Maintain",
    "reit": "Reiterate",
}

# Map common analyst grade strings to buy / hold / sell buckets
_BUY_GRADES  = {"buy", "strong buy", "outperform", "overweight",
                 "accumulate", "add", "positive", "top pick"}
_SELL_GRADES = {"sell", "strong sell", "underperform", "underweight",
                 "reduce", "negative", "avoid"}

def _grade_bucket(grade: str | None) -> str:
    """Return 'buy', 'hold', or 'sell' for a given grade string."""
    if not grade:
        return "hold"
    g = grade.lower().strip()
    if g in _BUY_GRADES:
        return "buy"
    if g in _SELL_GRADES:
        return "sell"
    return "hold"


def get_analyst_grades(ticker: str, limit: int = 10) -> list[dict]:
    """
    Get recent analyst rating changes from FMP.

    Substitutes Benzinga analyst ratings. Includes upgrades, downgrades,
    initiations, and maintained ratings.

    Note: FMP's historical-grade endpoint does not provide price targets.
    Price targets are available separately via the /v4/price-target endpoint.

    Returns a list of grade dicts with: analyst_firm, action, rating,
    rating_prior, published_at, bucket (buy | hold | sell).
    """
    log_provider_call(log, "FMP", f"/historical-grade/{ticker}", ticker)

    data = _get(f"/historical-grade/{ticker}", params={"limit": limit})
    if not data:
        raise ValueError(f"FMP returned no analyst grades for {ticker}")

    grades = []
    for item in (data or []):
        action_code = item.get("action", "")
        new_grade   = item.get("newGrade")
        grades.append({
            "ticker":             ticker.upper(),
            "analyst_firm":       item.get("gradingCompany"),
            "action":             _GRADE_ACTION_LABELS.get(action_code, action_code.capitalize()),
            "rating":             new_grade,
            "rating_prior":       item.get("previousGrade"),
            "price_target":       None,   # not available in this endpoint
            "price_target_prior": None,
            "published_at":       item.get("date"),
            "bucket":             _grade_bucket(new_grade),
            "provider":           "fmp",
        })
    return grades


def get_company_profile(ticker: str) -> dict:
    """
    Get company profile: name, sector, industry, description, market cap.
    Used by the sector-aware valuation engine to choose the right models.
    """
    log_provider_call(log, "FMP", f"/profile/{ticker}", ticker)
    data = _get(f"/profile/{ticker}")
    if not data:
        raise ValueError(f"FMP returned no profile for {ticker}")
    p = data[0] if isinstance(data, list) else data
    return {
        "ticker":      ticker.upper(),
        "name":        p.get("companyName"),
        "sector":      p.get("sector"),
        "industry":    p.get("industry"),
        "description": p.get("description"),
        "market_cap":  p.get("mktCap"),
        "exchange":    p.get("exchangeShortName"),
        "country":     p.get("country"),
        "source":      "fmp",
    }
