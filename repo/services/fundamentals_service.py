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
        income   = fmp.get_income_statement(ticker, limit=20)
        balance  = fmp.get_balance_sheet(ticker, limit=20)
        cashflow = fmp.get_cash_flow_statement(ticker, limit=20)
        income_source   = "fmp"
        income_fallback = False
        fmp_ok = True
    except Exception as e:
        log.warning(f"FMP financial statements failed for {ticker} — trying yfinance: {e}")

    if not fmp_ok:
        try:
            stmts    = yf_provider.get_financial_statements(ticker, limit=8)
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


def _normalise_growth(value) -> float | None:
    """
    Normalise a growth rate that may arrive as a decimal or percentage.

    Finnhub's revenueGrowthTTMYoy is documented as decimal (0.12 = 12%) but
    in practice returns percentage-expressed values for many tickers (12.0 = 12%).
    Without this guard the thesis generator multiplies by 100 again → 1200%.

    Rules:
      -1.5 to 3.0  → treat as decimal (already correct)
      -150 to 300  → treat as percentage, divide by 100
      outside both → discard (implausible, return None)
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if -1.5 <= v <= 3.0:
        return v
    if -150.0 <= v <= 300.0:
        return v / 100.0
    return None   # outside any plausible range — discard


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
        "revenue_growth_yoy": _normalise_growth(finnhub_m.get("revenue_growth_yoy")),
        "source":             "fmp+finnhub",
        "confidence":         82.0,
    }

    cache.set(cache_key, result, ttl)
    return result


def get_valuation_inputs(ticker: str, price: float | None = None, sector: str = "") -> dict:
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
        raw_yoy = float(finnhub_yoy)
        # Finnhub sometimes returns growth as a percentage (e.g. 5.18 meaning 5.18%)
        # rather than a decimal (0.0518). Detect and normalise.
        if -1.5 <= raw_yoy <= 3.0:
            revenue_growth = raw_yoy          # decimal — use as-is
        elif -150 <= raw_yoy <= 300:
            revenue_growth = raw_yoy / 100    # percentage format — convert
            warnings.append(f"Revenue growth from Finnhub normalised ({raw_yoy:.2f}% → decimal)")
        # else: outside any plausible range — discard, fall through to TTM calc

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

    # ── Analyst forward revenue estimates ─────────────────────────────────────
    # FMP consensus estimates for the next 1–2 fiscal years.
    # These anchor Stage 1 of the DCF. Falls back to historical growth if empty.
    analyst_rev_growth_y1   = None
    analyst_rev_growth_y2   = None
    analyst_count           = 0
    analyst_estimate_spread = None   # (high − low) / avg — proxy for disagreement

    try:
        est_data = fmp.get_analyst_estimates(ticker, limit=3)
        if est_data and revenue_ttm and revenue_ttm > 0:
            est0 = est_data[0]
            rev0 = est0.get("estimated_revenue_avg")
            if rev0 and rev0 > 0:
                analyst_rev_growth_y1 = (rev0 - revenue_ttm) / revenue_ttm
                rev_low  = est0.get("estimated_revenue_low")  or rev0
                rev_high = est0.get("estimated_revenue_high") or rev0
                analyst_estimate_spread = (rev_high - rev_low) / rev0
            analyst_count = max(
                est0.get("analyst_count_revenue") or 0,
                est0.get("analyst_count_eps")     or 0,
            )
            if len(est_data) >= 2:
                rev1 = est_data[1].get("estimated_revenue_avg")
                if rev1 and rev0 and rev0 > 0:
                    analyst_rev_growth_y2 = (rev1 - rev0) / rev0
    except Exception as e:
        log.warning(f"Analyst estimates unavailable for {ticker}: {e}")

    inputs["analyst_rev_growth_y1"]   = analyst_rev_growth_y1
    inputs["analyst_rev_growth_y2"]   = analyst_rev_growth_y2
    inputs["analyst_count"]           = analyst_count
    inputs["analyst_estimate_spread"] = analyst_estimate_spread

    # ── Analyst price target consensus ────────────────────────────────────────
    # Median PT is more robust than mean — less distorted by outlier bull/bear calls.
    # Stored as None for small caps / uncovered tickers; run_analyst_pt handles gracefully.
    analyst_pt_consensus = None
    analyst_pt_median    = None
    analyst_pt_high      = None
    analyst_pt_low       = None

    # Primary: FMP price-target-consensus (may require higher plan — falls back silently)
    try:
        pt_data = fmp.get_price_target_consensus(ticker)
        analyst_pt_consensus = pt_data.get("target_consensus")
        analyst_pt_median    = pt_data.get("target_median")
        analyst_pt_high      = pt_data.get("target_high")
        analyst_pt_low       = pt_data.get("target_low")
    except Exception as e:
        log.warning(f"FMP price target unavailable for {ticker}: {e}")

    # Fallback: Finnhub price target (free tier, broader coverage)
    if not analyst_pt_median and not analyst_pt_consensus:
        try:
            import providers.finnhub_provider as finnhub
            pt_data = finnhub.get_price_target(ticker)
            analyst_pt_consensus = pt_data.get("target_mean")
            analyst_pt_median    = pt_data.get("target_median")
            analyst_pt_high      = pt_data.get("target_high")
            analyst_pt_low       = pt_data.get("target_low")
        except Exception as e:
            log.warning(f"Finnhub price target unavailable for {ticker}: {e}")

    inputs["analyst_pt_consensus"] = analyst_pt_consensus
    inputs["analyst_pt_median"]    = analyst_pt_median
    inputs["analyst_pt_high"]      = analyst_pt_high
    inputs["analyst_pt_low"]       = analyst_pt_low

    # ── EBIT margin ───────────────────────────────────────────────────────────
    latest_income = income[0] if income else {}
    ebit_margin = latest_income.get("operating_margin")
    if ebit_margin is None and latest_income.get("operating_income") and latest_income.get("revenue"):
        ebit_margin = latest_income["operating_income"] / latest_income["revenue"]
    if ebit_margin is None:
        warnings.append("EBIT margin could not be calculated")
    inputs["ebit_margin"] = ebit_margin

    # ── Depreciation, Capex, and FCF (TTM = sum of last 4 quarters) ─────────
    # Tax rate is computed later in the WACC section from income statement data.
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

    # ── Effective tax rate from income statement ──────────────────────────────
    # TTM pretax income and tax expense give the actual rate this company pays.
    # Capped at [15%, 40%] to exclude loss-years and international anomalies.
    ttm_pretax = sum((q.get("pretax_income")      or 0) for q in income[:4])
    ttm_tax    = sum((q.get("income_tax_expense") or 0) for q in income[:4])
    if ttm_pretax > 0 and ttm_tax > 0:
        tax_rate = max(0.15, min(0.40, ttm_tax / ttm_pretax))
    else:
        tax_rate = 0.21   # US statutory rate — more accurate than the previous 20% default
        warnings.append("Effective tax rate defaulted to 21% — pretax income data unavailable")

    inputs["tax_rate"] = tax_rate

    # ── Beta and WACC estimate ────────────────────────────────────────────────
    # Step 1: Damodaran sector unlevered beta (more stable than company's own beta)
    from data.damodaran_betas import get_unlevered_beta, relevered_beta, DAMODARAN_ERP
    ul_beta = get_unlevered_beta(sector, "")

    # Step 2: Company debt from balance sheet
    total_debt_val   = latest_bal.get("total_debt")   or 0
    total_equity_val = latest_bal.get("total_equity") or 0

    # Step 3: Market equity — price × diluted shares (more accurate than book equity)
    # Falls back to book equity for WACC weights if price is unavailable.
    market_equity = (price * shares_out) if (price and shares_out) else None
    if market_equity is None and total_equity_val > 0:
        market_equity = total_equity_val   # book equity as last resort

    # Step 4: Re-lever sector beta for this company's actual capital structure
    if market_equity and market_equity > 0:
        beta_est = relevered_beta(ul_beta, total_debt_val, market_equity, tax_rate)
    else:
        # Fall back to Finnhub's raw beta if market equity is unknowable
        beta_est = (ratios or {}).get("beta") or ul_beta
        warnings.append("Re-levered beta unavailable — using Damodaran sector unlevered beta")

    # Step 5: Risk-free rate from FRED 10Y Treasury
    risk_free = 0.045
    baa_yield  = None
    try:
        from services.macro_service import get_macro_snapshot
        macro = get_macro_snapshot()
        if macro and macro.get("treasury_10y"):
            risk_free = (macro["treasury_10y"]["value"] or 4.5) / 100
        if macro and macro.get("baa_yield"):
            baa_yield = (macro["baa_yield"]["value"] or None)
            if baa_yield:
                baa_yield = baa_yield / 100
    except Exception:
        warnings.append("FRED rates unavailable — risk-free defaulted to 4.5%")

    # Step 6: Cost of equity (CAPM with Damodaran ERP)
    cost_of_equity = risk_free + beta_est * DAMODARAN_ERP

    # Step 7: Cost of debt via synthetic credit rating
    # Financials (banks/insurers) excluded: their "interest expense" is core operations,
    # not debt service, so the coverage ratio would be meaninglessly low.
    ttm_interest   = sum((q.get("interest_expense") or 0) for q in income[:4])
    ttm_ebit       = sum((q.get("operating_income") or 0) for q in income[:4])

    if sector == "Financials":
        # For banks/insurers, use FRED Baa yield as a reasonable proxy
        syn_spread   = baa_yield - risk_free if baa_yield and baa_yield > risk_free else 0.0138
        syn_rating   = "N/A (Financials)"
    else:
        from data.damodaran_betas import synthetic_default_spread
        syn_spread, syn_rating = synthetic_default_spread(ttm_ebit, ttm_interest)

    cost_of_debt = risk_free + syn_spread
    after_tax_kd = cost_of_debt * (1 - tax_rate)

    # Step 8: Capital structure weights using market equity (correct)
    # Negative-equity companies (MCD, KO) default to 100% equity weight.
    if market_equity and market_equity > 0 and total_debt_val > 0:
        total_capital = market_equity + total_debt_val
        e_weight      = market_equity    / total_capital
        d_weight      = total_debt_val   / total_capital
        wacc_estimate = (e_weight * cost_of_equity) + (d_weight * after_tax_kd)
    else:
        wacc_estimate = cost_of_equity   # no debt or no equity — WACC = Ke

    inputs["beta"]            = round(beta_est, 3)
    inputs["wacc_estimate"]   = round(wacc_estimate, 4)
    inputs["terminal_growth"] = 0.03   # standard 3% perpetuity growth

    # Store WACC components for transparency in the research output
    inputs["wacc_components"] = {
        "risk_free":        round(risk_free, 4),
        "beta":             round(beta_est, 3),
        "erp":              DAMODARAN_ERP,
        "cost_of_equity":   round(cost_of_equity, 4),
        "synthetic_rating": syn_rating,
        "default_spread":   round(syn_spread, 4),
        "cost_of_debt":     round(cost_of_debt, 4),
        "after_tax_kd":     round(after_tax_kd, 4),
        "equity_weight":    round(e_weight if (market_equity and total_debt_val > 0) else 1.0, 3),
        "debt_weight":      round(d_weight if (market_equity and total_debt_val > 0) else 0.0, 3),
        "tax_rate":         round(tax_rate, 3),
        "source":           "Damodaran 2025 sector betas + FRED rates + synthetic rating",
    }

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
