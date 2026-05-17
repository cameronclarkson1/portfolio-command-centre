"""
yfinance_provider.py — Emergency fallback using the yfinance library.

yfinance wraps Yahoo Finance's unofficial API. It is free and requires no API key,
making it a reliable last resort when all paid providers fail.

Use this ONLY when Polygon, FMP, and Finnhub have all failed.
Do NOT use it as a primary source — it can be unstable and rate-limited.
"""

import yfinance as yf
from datetime import datetime, timezone

from config.settings import INDEX_TICKERS_YFINANCE
from utils.logging_utils import get_logger, log_provider_call

log = get_logger(__name__)


def get_quote(ticker: str) -> dict:
    """
    Get current price data for a ticker using yfinance.
    Falls back to Yahoo Finance's fast_info endpoint.

    Returns: ticker, price, change_pct, volume, market_cap, source, fetched_at
    """
    log_provider_call(log, "yfinance", f"Ticker({ticker}).fast_info", ticker)

    t = yf.Ticker(ticker)
    info = t.fast_info

    price      = getattr(info, "last_price",       None)
    prev_close = getattr(info, "previous_close",   None)
    volume     = getattr(info, "last_volume",       None)
    market_cap = getattr(info, "market_cap",        None)

    change_pct = 0.0
    if price and prev_close and prev_close != 0:
        change_pct = (price - prev_close) / prev_close

    if price is None:
        raise ValueError(f"yfinance returned no price for {ticker}")

    return {
        "ticker":     ticker.upper(),
        "price":      price,
        "change_pct": change_pct,
        "volume":     volume,
        "market_cap": market_cap,
        "source":     "yfinance",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_candles(ticker: str, period: str = "1y", interval: str = "1d") -> list[dict]:
    """
    Get OHLCV candle history using yfinance.

    Args:
        ticker:   Stock ticker
        period:   "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"
        interval: "1m", "5m", "15m", "1h", "1d", "1wk", "1mo"

    Returns a list of candle dicts with: date, open, high, low, close, volume
    """
    log_provider_call(log, "yfinance", f"Ticker({ticker}).history(period={period})", ticker)

    t    = yf.Ticker(ticker)
    hist = t.history(period=period, interval=interval)

    if hist.empty:
        raise ValueError(f"yfinance returned no candle data for {ticker}")

    candles = []
    for date, row in hist.iterrows():
        candles.append({
            "date":   date.strftime("%Y-%m-%d"),
            "open":   round(float(row["Open"]),   4),
            "high":   round(float(row["High"]),   4),
            "low":    round(float(row["Low"]),    4),
            "close":  round(float(row["Close"]),  4),
            "volume": int(row["Volume"]),
        })

    return candles


def get_index_snapshots() -> list[dict]:
    """
    Get current values for S&P 500, NASDAQ, Dow Jones, and VIX using yfinance.
    This is the most reliable fallback for index data.

    Returns a list of dicts with: name, value, change_pct, source, fetched_at
    """
    log_provider_call(log, "yfinance", f"download({list(INDEX_TICKERS_YFINANCE.values())})")

    now = datetime.now(timezone.utc).isoformat()
    indices = []

    for name, yf_ticker in INDEX_TICKERS_YFINANCE.items():
        try:
            t    = yf.Ticker(yf_ticker)
            info = t.fast_info

            price      = getattr(info, "last_price",     None)
            prev_close = getattr(info, "previous_close", None)

            change_pct = 0.0
            if price and prev_close and prev_close != 0:
                change_pct = (price - prev_close) / prev_close

            indices.append({
                "name":       name,
                "value":      price,
                "change_pct": change_pct,
                "source":     "yfinance",
                "fetched_at": now,
            })
        except Exception as e:
            log.warning(f"yfinance: could not fetch index {name} ({yf_ticker}): {e}")
            indices.append({
                "name":       name,
                "value":      None,
                "change_pct": 0.0,
                "source":     "yfinance",
                "fetched_at": now,
            })

    return indices


def get_financial_statements(ticker: str, limit: int = 4) -> dict:
    """
    Get quarterly income statement, balance sheet, and cash flow from yfinance.
    Used as a fallback when FMP financial statements are unavailable.

    Returns the same structure as fundamentals_service expects:
      { "income": [...], "balance": [...], "cashflow": [...] }
    """
    log_provider_call(log, "yfinance", f"Ticker({ticker}).quarterly_financials", ticker)

    t = yf.Ticker(ticker)

    def _safe_val(df, row_candidates, col):
        """Return the first matching row value for a column, or None."""
        for row in row_candidates:
            try:
                val = df.loc[row, col]
                if val is not None and str(val) != "nan":
                    return float(val)
            except (KeyError, TypeError):
                continue
        return None

    # ── Income statement ─────────────────────────────────────────────────────
    income = []
    try:
        fin = t.quarterly_financials  # rows=items, cols=dates (newest first)
        if fin is not None and not fin.empty:
            for col in list(fin.columns)[:limit]:
                date_str = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
                revenue        = _safe_val(fin, ["Total Revenue"],                             col)
                gross_profit   = _safe_val(fin, ["Gross Profit"],                               col)
                op_income      = _safe_val(fin, ["Operating Income", "EBIT"],                   col)
                net_income     = _safe_val(fin, ["Net Income", "Net Income Common Stockholders"], col)
                ebitda         = _safe_val(fin, ["EBITDA", "Normalized EBITDA"],                col)
                eps            = _safe_val(fin, ["Diluted EPS", "Basic EPS"],                   col)
                gross_margin   = (gross_profit / revenue) if (revenue and gross_profit) else None
                op_margin      = (op_income    / revenue) if (revenue and op_income)    else None
                income.append({
                    "period":           date_str[:7],
                    "date":             date_str,
                    "revenue":          revenue,
                    "gross_profit":     gross_profit,
                    "operating_income": op_income,
                    "net_income":       net_income,
                    "ebitda":           ebitda,
                    "eps":              eps,
                    "gross_margin":     gross_margin,
                    "operating_margin": op_margin,
                    "net_margin":       (net_income / revenue) if (revenue and net_income) else None,
                })
    except Exception as e:
        log.warning(f"yfinance income statement failed for {ticker}: {e}")

    # ── Balance sheet ─────────────────────────────────────────────────────────
    balance = []
    try:
        bs = t.quarterly_balance_sheet
        if bs is not None and not bs.empty:
            for col in list(bs.columns)[:limit]:
                date_str = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
                cash        = _safe_val(bs, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"], col)
                total_assets = _safe_val(bs, ["Total Assets"],                                     col)
                total_liab   = _safe_val(bs, ["Total Liabilities Net Minority Interest", "Total Liabilities"], col)
                total_equity = _safe_val(bs, ["Total Equity Gross Minority Interest", "Stockholders Equity", "Total Stockholders Equity"], col)
                total_debt   = _safe_val(bs, ["Total Debt", "Long Term Debt"],                      col)
                net_debt     = _safe_val(bs, ["Net Debt"],                                           col)
                if net_debt is None and total_debt is not None and cash is not None:
                    net_debt = total_debt - cash
                shares       = _safe_val(bs, ["Ordinary Shares Number", "Share Issued"],             col)
                balance.append({
                    "period":             date_str[:7],
                    "date":               date_str,
                    "cash":               cash,
                    "total_assets":       total_assets,
                    "total_liabilities":  total_liab,
                    "total_equity":       total_equity,
                    "total_debt":         total_debt,
                    "net_debt":           net_debt,
                    "shares_outstanding": shares,
                })
    except Exception as e:
        log.warning(f"yfinance balance sheet failed for {ticker}: {e}")

    # ── Cash flow ─────────────────────────────────────────────────────────────
    cashflow = []
    try:
        cf = t.quarterly_cashflow
        if cf is not None and not cf.empty:
            for col in list(cf.columns)[:limit]:
                date_str = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
                op_cf   = _safe_val(cf, ["Operating Cash Flow", "Cash Flows From Operations"], col)
                capex   = _safe_val(cf, ["Capital Expenditure", "Purchase Of PPE"],             col)
                fcf     = _safe_val(cf, ["Free Cash Flow"],                                     col)
                if fcf is None and op_cf is not None and capex is not None:
                    fcf = op_cf + capex   # capex is usually negative in yfinance
                dep     = _safe_val(cf, ["Depreciation Amortization Depletion", "Depreciation And Amortization", "Depreciation"], col)
                divs    = _safe_val(cf, ["Common Stock Dividend Paid", "Cash Dividends Paid"], col)
                cashflow.append({
                    "period":              date_str[:7],
                    "date":               date_str,
                    "operating_cash_flow": op_cf,
                    "capex":              capex,
                    "free_cash_flow":     fcf,
                    "depreciation":       dep,
                    "dividends_paid":     divs,
                })
    except Exception as e:
        log.warning(f"yfinance cash flow failed for {ticker}: {e}")

    if not income and not balance and not cashflow:
        raise ValueError(f"yfinance returned no financial statements for {ticker}")

    return {"income": income, "balance": balance, "cashflow": cashflow}


def get_info(ticker: str) -> dict:
    """
    Get company profile and fundamentals using yfinance.
    Useful when FMP and Finnhub are unavailable.

    Returns a dict with company name, sector, industry, and key metrics.
    """
    log_provider_call(log, "yfinance", f"Ticker({ticker}).info", ticker)

    t    = yf.Ticker(ticker)
    info = t.info  # Note: this is slower than fast_info but contains more fields

    return {
        "ticker":          ticker.upper(),
        "name":            info.get("longName") or info.get("shortName"),
        "sector":          info.get("sector"),
        "industry":        info.get("industry"),
        "description":     info.get("longBusinessSummary"),
        "employees":       info.get("fullTimeEmployees"),
        "pe_ratio":        info.get("trailingPE"),
        "forward_pe":      info.get("forwardPE"),
        "peg_ratio":       info.get("pegRatio"),
        "ps_ratio":        info.get("priceToSalesTrailing12Months"),
        "pb_ratio":        info.get("priceToBook"),
        "dividend_yield":  info.get("dividendYield"),
        "beta":            info.get("beta"),
        "52_week_high":    info.get("fiftyTwoWeekHigh"),
        "52_week_low":     info.get("fiftyTwoWeekLow"),
        "source":          "yfinance",
        "fetched_at":      datetime.now(timezone.utc).isoformat(),
    }
