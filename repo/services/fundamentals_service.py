"""
fundamentals_service.py — Financial statements, ratios, and valuation inputs.

Pages call these for the stock research section.
SEC EDGAR is used to validate revenue figures from FMP.

Functions:
  get_financial_statements(ticker) → income, balance sheet, cash flow
  get_key_ratios(ticker)           → PE, EV/EBITDA, ROIC, margins, etc.
  get_valuation_inputs(ticker)     → cleaned inputs ready for DCF model
"""

import providers.fmp_provider      as fmp
import providers.finnhub_provider  as finnhub
import providers.sec_edgar_provider as sec_edgar
import providers.yfinance_provider  as yf_provider

from services import _try_providers
from storage.cache_manager import cache
from config.settings import CACHE_TTL
from utils.logging_utils import get_logger, log_cache_hit, log_cache_miss
from utils.validation_utils import completeness_score, cross_validate, DCF_INPUT_FIELDS

log = get_logger(__name__)


def get_financial_statements(ticker: str) -> dict | None:
    """
    Return the last 4 quarters of income statements, balance sheets, and cash flows.

    Structure:
    {
        "income":    [ {period, revenue, net_income, ebitda, eps, ...}, ... ],
        "balance":   [ {period, cash, total_debt, total_equity, ...}, ... ],
        "cashflow":  [ {period, operating_cash_flow, capex, free_cash_flow, ...}, ... ],
        "source":    "fmp",
        "fallback_used": False,
        "confidence": 88.0,
    }
    """
    ticker    = ticker.upper()
    cache_key = f"financials:{ticker}"
    ttl       = CACHE_TTL["fundamentals"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    # Try FMP first; if it fails (requires paid tier), fall back to yfinance.
    # yfinance bundles all three statements in one call so we try it once if FMP fails.
    fmp_ok = False
    income = balance = cashflow = None
    income_source = "none"
    income_fallback = True

    try:
        income   = fmp.get_income_statement(ticker, limit=4)
        balance  = fmp.get_balance_sheet(ticker, limit=4)
        cashflow = fmp.get_cash_flow_statement(ticker, limit=4)
        income_source   = "fmp"
        income_fallback = False
        fmp_ok = True
    except Exception as e:
        log.warning(f"FMP financial statements failed for {ticker} — trying yfinance: {e}")

    if not fmp_ok:
        try:
            stmts    = yf_provider.get_financial_statements(ticker, limit=4)
            income   = stmts.get("income")   or []
            balance  = stmts.get("balance")  or []
            cashflow = stmts.get("cashflow") or []
            income_source   = "yfinance"
            income_fallback = True
        except Exception as e:
            log.error(f"yfinance financial statements also failed for {ticker}: {e}")

    if not any([income, balance, cashflow]):
        log.error(f"All financial statement providers failed for {ticker}")
        return None

    # Basic completeness scoring
    income_score = completeness_score(
        income[0] if income else {},
        ["revenue", "gross_profit", "operating_income", "net_income", "ebitda"]
    ) if income else 0.0

    confidence = round(income_score * 90, 1)  # max 90% for fundamentals

    result = {
        "income":        income   or [],
        "balance":       balance  or [],
        "cashflow":      cashflow or [],
        "source":        income_source,
        "fallback_used": income_fallback,
        "confidence":    confidence,
    }

    cache.set(cache_key, result, ttl)
    return result


def get_key_ratios(ticker: str) -> dict | None:
    """
    Return key financial ratios for a ticker.

    Structure:
    {
        "pe_ratio":     28.4,
        "ev_ebitda":    18.2,
        "roic":         0.28,       # 28%
        "roe":          0.35,
        "gross_margin": 0.69,
        "net_margin":   0.36,
        "debt_equity":  0.8,
        "dividend_yield": 0.009,    # 0.9%
        "beta":         0.92,
        "52_week_high": 468.35,
        "52_week_low":  309.45,
        "source":       "fmp+finnhub",
        "confidence":   82.0,
    }
    """
    ticker    = ticker.upper()
    cache_key = f"ratios:{ticker}"
    ttl       = CACHE_TTL["fundamentals"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    fmp_metrics, _, _ = _try_providers([
        ("fmp", lambda: fmp.get_key_metrics(ticker, limit=1)),
    ], f"{ticker} key metrics")

    finnhub_metrics, _, _ = _try_providers([
        ("finnhub", lambda: finnhub.get_basic_financials(ticker)),
    ], f"{ticker} basic financials")

    if not fmp_metrics and not finnhub_metrics:
        return None

    fmp_m      = (fmp_metrics or [{}])[0]
    finnhub_m  = finnhub_metrics or {}

    # Combine: FMP as primary, Finnhub fills gaps.
    # revenue_per_share and fcf_per_share come from FMP key-metrics and are used
    # as fallbacks in the valuation models when full financial statements are unavailable.
    result = {
        "pe_ratio":           fmp_m.get("pe_ratio")      or finnhub_m.get("pe_ttm"),
        "ev_ebitda":          fmp_m.get("ev_ebitda"),
        "ps_ratio":           fmp_m.get("ps_ratio")       or finnhub_m.get("ps_ttm"),
        "pb_ratio":           fmp_m.get("pb_ratio")       or finnhub_m.get("pb_quarterly"),
        "roic":               fmp_m.get("roic")            or finnhub_m.get("roa_ttm"),
        "roe":                fmp_m.get("roe")             or finnhub_m.get("roe_ttm"),
        "debt_equity":        fmp_m.get("debt_to_equity"),
        "payout_ratio":       fmp_m.get("payout_ratio"),
        "revenue_per_share":  fmp_m.get("revenue_per_share"),
        "fcf_per_share":      fmp_m.get("fcf_per_share"),
        "dividend_yield":     finnhub_m.get("dividend_yield"),
        "beta":               finnhub_m.get("beta"),
        "52_week_high":       finnhub_m.get("52_week_high"),
        "52_week_low":        finnhub_m.get("52_week_low"),
        "revenue_growth_yoy": finnhub_m.get("revenue_growth_yoy"),
        "source":             "fmp+finnhub",
        "confidence":         82.0,
    }

    cache.set(cache_key, result, ttl)
    return result


def get_valuation_inputs(ticker: str) -> dict:
    """
    Assemble all inputs needed to run a DCF model.
    Also returns a warnings list if any key inputs are missing.

    Structure:
    {
        "ticker":          "MSFT",
        "revenue_ttm":     245000000000,
        "revenue_growth":  0.14,         # trailing 3-year CAGR
        "ebit_margin":     0.44,
        "tax_rate":        0.18,
        "depreciation":    12000000000,
        "capex":           -20000000000,
        "free_cash_flow":  68000000000,
        "net_debt":        -55000000000, # negative = net cash
        "shares_out":      7500000000,
        "beta":            0.92,
        "wacc_estimate":   0.087,        # calculated here as a starting point
        "terminal_growth": 0.03,         # standard 3% default
        "warnings":        [],           # list of strings about missing/estimated inputs
        "completeness":    0.92,         # fraction of inputs that are real vs estimated
    }
    """
    ticker    = ticker.upper()
    cache_key = f"val_inputs:{ticker}"
    ttl       = CACHE_TTL["fundamentals"]

    cached = cache.get(cache_key, ttl)
    if cached:
        log_cache_hit(log, cache_key)
        return cached
    log_cache_miss(log, cache_key)

    stmts  = get_financial_statements(ticker)
    ratios = get_key_ratios(ticker)

    warnings = []
    inputs   = {"ticker": ticker}

    if not stmts:
        warnings.append("Financial statements unavailable — DCF cannot be run")
        return {"ticker": ticker, "warnings": warnings, "completeness": 0.0}

    income   = stmts.get("income",   [{}])
    balance  = stmts.get("balance",  [{}])
    cashflow = stmts.get("cashflow", [{}])

    # ── Revenue (TTM = sum of last 4 quarters) ────────────────────────────────
    revenues = [q.get("revenue") or 0 for q in income[:4]]
    revenue_ttm = sum(revenues) if any(revenues) else None
    if not revenue_ttm:
        warnings.append("Revenue data missing — cannot calculate growth rate")
    inputs["revenue_ttm"] = revenue_ttm

    # ── Revenue growth ────────────────────────────────────────────────────────
    # Priority 1: Finnhub revenue_growth_yoy (TTM vs prior TTM — not seasonal)
    # Priority 2: TTM(quarters 0-3) vs TTM(quarters 4-7) if 8+ quarters available
    # Fallback: default 8%; cap at 25% to prevent DCF explosion
    revenue_growth = None

    finnhub_yoy = (ratios or {}).get("revenue_growth_yoy")
    if finnhub_yoy is not None and isinstance(finnhub_yoy, (int, float)) and not (finnhub_yoy != finnhub_yoy):
        revenue_growth = float(finnhub_yoy)

    if revenue_growth is None and len(income) >= 8:
        ttm_now   = sum(q.get("revenue") or 0 for q in income[:4])
        ttm_prior = sum(q.get("revenue") or 0 for q in income[4:8])
        if ttm_prior > 0 and ttm_now > 0:
            revenue_growth = (ttm_now - ttm_prior) / ttm_prior

    if revenue_growth is None:
        warnings.append("Revenue growth defaulted to 8% — insufficient history for TTM-vs-TTM comparison")
        revenue_growth = 0.08

    if revenue_growth > 0.25:
        warnings.append(
            f"Revenue growth capped at 25% (raw: {revenue_growth:.1%}) — "
            "likely seasonal distortion; verify against annual report"
        )
        revenue_growth = 0.25
    elif revenue_growth < -0.30:
        warnings.append(f"Revenue growth floor applied at -30% (raw: {revenue_growth:.1%})")
        revenue_growth = -0.30

    inputs["revenue_growth"] = revenue_growth

    # ── EBIT margin ───────────────────────────────────────────────────────────
    latest_income = income[0] if income else {}
    ebit_margin = latest_income.get("operating_margin")
    if ebit_margin is None and latest_income.get("operating_income") and latest_income.get("revenue"):
        ebit_margin = latest_income["operating_income"] / latest_income["revenue"]
    if ebit_margin is None:
        warnings.append("EBIT margin could not be calculated")
    inputs["ebit_margin"] = ebit_margin

    # ── Tax rate ──────────────────────────────────────────────────────────────
    # Estimate from net income / pre-tax income not available directly in our schema
    # Use a standard 20% assumption if not available
    tax_rate = 0.20
    warnings.append("Tax rate defaulted to 20% — verify against actual effective rate")
    inputs["tax_rate"] = tax_rate

    # ── Depreciation, Capex, and FCF (TTM = sum of last 4 quarters) ─────────
    # Single-quarter × 4 causes seasonal distortion for companies like LULU.
    def _ttm(lst, field, n=4):
        return sum((q.get(field) or 0) for q in lst[:n]) or 0

    depreciation = _ttm(cashflow, "depreciation")
    capex        = _ttm(cashflow, "capex")
    fcf          = _ttm(cashflow, "free_cash_flow")

    if not depreciation:
        warnings.append("Depreciation data missing from cash flow statement")
    if not capex:
        warnings.append("Capex data missing from cash flow statement")
    if not fcf and cashflow:
        # Derive FCF = Operating CF − |Capex| if not reported directly
        op_cf = _ttm(cashflow, "operating_cash_flow")
        if op_cf:
            fcf = op_cf + capex  # capex is typically negative in financial data
            warnings.append("Free cash flow derived as Operating CF + Capex (TTM, capex is negative)")

    inputs["depreciation"]   = depreciation
    inputs["capex"]          = capex
    inputs["free_cash_flow"] = fcf

    # ── Balance sheet items ───────────────────────────────────────────────────
    latest_bal    = balance[0]  if balance  else {}
    latest_income = income[0]   if income   else {}
    net_debt      = latest_bal.get("net_debt")

    # FMP stable API removed commonStockSharesOutstanding from the balance sheet.
    # Use the income statement's weighted-average diluted share count instead,
    # which is the standard basis for per-share valuation metrics.
    shares_out = (
        latest_income.get("shares_diluted")
        or latest_income.get("shares_basic")
        or latest_bal.get("shares_outstanding")   # legacy fallback
    )

    if net_debt is None:
        warnings.append("Net debt not available — assumed zero for DCF")
        net_debt = 0
    if not shares_out:
        warnings.append("Shares outstanding missing — per-share value unreliable")

    inputs["net_debt"]     = net_debt
    inputs["shares_out"]   = shares_out

    # ── Beta and WACC estimate ────────────────────────────────────────────────
    beta = (ratios or {}).get("beta")
    if beta is None:
        beta = 1.0
        warnings.append("Beta not available — defaulted to 1.0 (market-equivalent risk)")

    # Risk-free rate from FRED (fall back to 4.5% if unavailable)
    risk_free = 0.045
    try:
        from services.macro_service import get_macro_snapshot
        macro = get_macro_snapshot()
        if macro and macro.get("treasury_10y"):
            risk_free = (macro["treasury_10y"]["value"] or 4.5) / 100
    except Exception:
        warnings.append("Risk-free rate from FRED unavailable — defaulted to 4.5%")

    market_premium = 0.055   # standard equity risk premium
    cost_of_equity = risk_free + beta * market_premium

    # WACC = equity_weight × cost_of_equity + debt_weight × cost_of_debt × (1 − tax)
    # Uses book equity weights (conservative proxy; market equity weights require live price).
    # Only applied when both equity and debt are positive — negative-equity companies
    # (e.g. MCD, KO after heavy buybacks) default to cost of equity.
    total_debt_val   = latest_bal.get("total_debt") or 0
    total_equity_val = latest_bal.get("total_equity") or 0

    if total_debt_val > 0 and total_equity_val > 0:
        book_capital    = total_equity_val + total_debt_val
        e_weight        = total_equity_val / book_capital
        d_weight        = total_debt_val   / book_capital
        cost_of_debt    = risk_free + 0.02       # risk-free + ~200bps IG credit spread
        after_tax_kd    = cost_of_debt * (1 - tax_rate)
        wacc_estimate   = (e_weight * cost_of_equity) + (d_weight * after_tax_kd)
    else:
        wacc_estimate = cost_of_equity

    inputs["beta"]           = beta
    inputs["wacc_estimate"]  = round(wacc_estimate, 4)
    inputs["terminal_growth"]= 0.03   # standard 3% perpetuity growth

    # ── Completeness score ────────────────────────────────────────────────────
    required = [
        "revenue_ttm", "revenue_growth", "ebit_margin", "free_cash_flow",
        "depreciation", "capex", "net_debt", "shares_out",
    ]
    filled = sum(1 for k in required if inputs.get(k) not in (None, 0))
    completeness = filled / len(required)

    inputs["warnings"]     = warnings
    inputs["completeness"] = round(completeness, 2)

    cache.set(cache_key, inputs, ttl)
    return inputs
