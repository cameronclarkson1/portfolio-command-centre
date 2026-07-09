"""
relative_valuation.py — Comparable/multiple-based valuation models.

Models: P/E, EV/EBITDA, EV/Sales, Price-to-Book, Price-to-Cash-Flow.

Each model compares the stock's fundamentals against sector benchmark multiples.
All income/cashflow figures are annualised as TTM (sum of last 4 quarters).
"""

# ── Sector benchmark multiples (2024-2025 long-run averages) ──────────────────
# These are approximate historical averages, not current peaks.
# Updated annually.

PE_BENCHMARKS = {
    "technology":             28,
    "consumer_discretionary": 22,
    "consumer_staples":       20,
    "financials":             13,
    "insurance":              12,
    "reit":                   35,
    "utilities":              18,
    "energy":                 11,
    "materials":              15,
    "industrials":            21,
    "healthcare":             22,
    "communication":          18,
    "early_stage":            None,   # P/E not applicable for negative earners
    "default":                20,
}

EV_EBITDA_BENCHMARKS = {
    "technology":             20,
    "consumer_discretionary": 13,
    "consumer_staples":       13,
    "utilities":              11,
    "energy":                  8,
    "materials":              10,
    "industrials":            14,
    "healthcare":             16,
    "communication":          12,
    "default":                13,
}

EV_SALES_BENCHMARKS = {
    "technology":             6.0,
    "consumer_discretionary": 1.5,
    "consumer_staples":       1.5,
    "healthcare":             3.0,
    "communication":          2.5,
    "energy":                 1.5,
    "materials":              1.5,
    "industrials":            2.0,
    "early_stage":            8.0,
    "default":                2.5,
}

PB_BENCHMARKS = {
    "financials":  1.5,
    "insurance":   1.4,
    "reit":        1.8,
    "utilities":   1.5,
    "materials":   2.0,
    "default":     3.5,
}

PCF_BENCHMARKS = {
    "energy":                  8,
    "materials":              12,
    "utilities":              15,
    "industrials":            14,
    "consumer_discretionary": 12,
    "default":                14,
}


def _ttm_income(statements: dict) -> dict:
    """Sum the last 4 quarters of income statement for TTM figures."""
    income = statements.get("income") or []
    ttm = {}
    for field in ("revenue", "gross_profit", "operating_income", "net_income", "ebitda", "eps"):
        ttm[field] = sum((q.get(field) or 0) for q in income[:4]) or None
    return ttm


def _ttm_cashflow(statements: dict) -> dict:
    """Sum the last 4 quarters of cash flow for TTM figures."""
    cashflow = statements.get("cashflow") or []
    ttm = {}
    for field in ("operating_cash_flow", "capex", "free_cash_flow"):
        ttm[field] = sum((q.get(field) or 0) for q in cashflow[:4]) or None
    return ttm


def _latest_balance(statements: dict) -> dict:
    """Return the most recent balance sheet (point-in-time)."""
    balance = statements.get("balance") or [{}]
    return balance[0] if balance else {}


def _get_shares(statements: dict) -> float | None:
    """
    Get diluted share count, trying balance sheet first then income statement.

    FMP's stable API no longer returns shares_outstanding on the balance sheet,
    so we fall back to weighted-average diluted shares from the income statement.
    """
    bal    = _latest_balance(statements)
    shares = bal.get("shares_outstanding")
    if not shares:
        income = statements.get("income") or [{}]
        latest = income[0] if income else {}
        shares = latest.get("shares_diluted") or latest.get("shares_basic")
    return shares


def run_pe(bucket: str, ratios: dict, statements: dict, price: float = 0) -> dict:
    """P/E comparable valuation: Fair Value = TTM EPS × sector average P/E.
    Falls back to inferring EPS from the live P/E ratio when statements are unavailable."""
    benchmark = PE_BENCHMARKS.get(bucket, PE_BENCHMARKS["default"])
    if benchmark is None:
        return {"model": "pe", "name": "P/E Comparable", "fair_value": None,
                "confidence": 0.0, "inputs_used": {},
                "warnings": ["P/E not applicable — company has negative or no earnings"]}

    warnings = []
    ttm = _ttm_income(statements)
    eps = ttm.get("eps")

    if not eps or eps <= 0:
        # Fallback: infer EPS from the live P/E ratio and current price
        live_pe = (ratios or {}).get("pe_ratio")
        if live_pe and live_pe > 0 and price:
            eps = price / live_pe
            warnings.append("EPS inferred from live P/E ratio (quarterly statements unavailable from API)")
        else:
            return {"model": "pe", "name": "P/E Comparable", "fair_value": None,
                    "confidence": 0.0, "inputs_used": {},
                    "warnings": ["Cannot use P/E — EPS unavailable and no live P/E ratio to fall back on"]}

    confidence = 55.0 if warnings else 65.0
    return {
        "model":      "pe",
        "name":       "P/E Comparable",
        "fair_value": round(eps * benchmark, 2),
        "confidence": confidence,
        "inputs_used": {"eps_ttm": round(eps, 4), "sector_pe_benchmark": benchmark},
        "warnings":   warnings + [f"Uses sector average P/E of {benchmark}× — individual quality premium not applied"],
    }


def run_ev_ebitda(bucket: str, ratios: dict, statements: dict) -> dict:
    """EV/EBITDA valuation: Implied EV = EBITDA × benchmark, then subtract net debt."""
    benchmark = EV_EBITDA_BENCHMARKS.get(bucket, EV_EBITDA_BENCHMARKS["default"])

    ttm        = _ttm_income(statements)
    bal        = _latest_balance(statements)
    ebitda     = ttm.get("ebitda")
    net_debt   = bal.get("net_debt") or 0
    shares_out = _get_shares(statements)

    if not ebitda or ebitda <= 0 or not shares_out:
        return {"model": "ev_ebitda", "name": "EV/EBITDA Comparable", "fair_value": None,
                "confidence": 0.0, "inputs_used": {},
                "warnings": ["Cannot use EV/EBITDA — EBITDA is negative/unavailable or share count missing"]}

    implied_ev   = ebitda * benchmark
    equity_value = implied_ev - net_debt
    fair_value   = equity_value / shares_out

    return {
        "model":      "ev_ebitda",
        "name":       "EV/EBITDA Comparable",
        "fair_value": round(fair_value, 2),
        "confidence": 63.0,
        "inputs_used": {
            "ebitda_ttm":            round(ebitda, 0),
            "sector_ev_ebitda":      benchmark,
            "net_debt":              net_debt,
            "shares_out":            shares_out,
        },
        "warnings": [f"Uses sector average EV/EBITDA of {benchmark}× — individual quality not adjusted"],
    }


def run_ev_sales(bucket: str, ratios: dict, statements: dict, price: float = 0) -> dict:
    """EV/Sales valuation: Implied EV = Revenue × benchmark, then subtract net debt.
    Falls back to using revenue-per-share from key metrics when statements are unavailable."""
    benchmark = EV_SALES_BENCHMARKS.get(bucket, EV_SALES_BENCHMARKS["default"])

    warnings = []
    ttm        = _ttm_income(statements)
    bal        = _latest_balance(statements)
    revenue    = ttm.get("revenue")
    net_debt   = bal.get("net_debt") or 0
    shares_out = bal.get("shares_outstanding")

    if revenue and shares_out:
        implied_ev   = revenue * benchmark
        equity_value = implied_ev - net_debt
        fair_value   = equity_value / shares_out
        confidence   = 58.0
    else:
        # Fallback: use revenue-per-share from FMP key-metrics or infer from live P/S ratio
        rev_per_share = (ratios or {}).get("revenue_per_share")
        if not rev_per_share and price:
            ps = (ratios or {}).get("ps_ratio")
            if ps and ps > 0:
                rev_per_share = price / ps
                warnings.append("Revenue per share inferred from live P/S ratio (statements unavailable)")
        if rev_per_share and rev_per_share > 0:
            fair_value = rev_per_share * benchmark
            confidence = 50.0
            warnings.append("Net debt not deducted — using per-share revenue directly")
        else:
            return {"model": "ev_sales", "name": "EV/Sales (Revenue Multiple)", "fair_value": None,
                    "confidence": 0.0, "inputs_used": {},
                    "warnings": ["Cannot use EV/Sales — revenue and per-share data both unavailable"]}

    return {
        "model":      "ev_sales",
        "name":       "EV/Sales (Revenue Multiple)",
        "fair_value": round(fair_value, 2),
        "confidence": confidence,
        "inputs_used": {
            "revenue_per_share": round(revenue / shares_out if (revenue and shares_out) else (ratios or {}).get("revenue_per_share") or 0, 2),
            "sector_ev_sales":   benchmark,
        },
        "warnings": warnings + [f"Uses sector average EV/Sales of {benchmark}×"],
    }


def run_pb(bucket: str, ratios: dict, statements: dict, price: float = 0) -> dict:
    """Price-to-Book valuation: Fair Value = (Total Equity / Shares) × sector P/B benchmark.
    Falls back to inferring book value per share from the live P/B ratio."""
    benchmark  = PB_BENCHMARKS.get(bucket, PB_BENCHMARKS["default"])
    bal        = _latest_balance(statements)
    equity     = bal.get("total_equity")
    shares_out = _get_shares(statements)

    warnings = []
    if equity and shares_out:
        bvps = equity / shares_out
        confidence = 62.0
    else:
        # Fallback: infer book value per share from live P/B ratio and price
        pb = (ratios or {}).get("pb_ratio")
        if pb and pb > 0 and price:
            bvps = price / pb
            confidence = 52.0
            warnings.append("Book value per share inferred from live P/B ratio (balance sheet unavailable)")
        else:
            return {"model": "pb", "name": "Price-to-Book", "fair_value": None,
                    "confidence": 0.0, "inputs_used": {},
                    "warnings": ["Cannot use P/B — book value unavailable and no live P/B ratio to fall back on"]}

    fair_value = bvps * benchmark
    return {
        "model":      "pb",
        "name":       "Price-to-Book",
        "fair_value": round(fair_value, 2),
        "confidence": confidence,
        "inputs_used": {
            "book_value_per_share": round(bvps, 2),
            "sector_pb_benchmark":  benchmark,
        },
        "warnings": warnings + [f"Uses sector average P/B of {benchmark}×"],
    }


def run_pcf(bucket: str, ratios: dict, statements: dict, price: float = 0) -> dict:
    """Price-to-Cash-Flow valuation: Fair Value = (TTM Operating CF / Shares) × benchmark.
    Falls back to FCF-per-share from FMP key metrics when statements are unavailable."""
    benchmark  = PCF_BENCHMARKS.get(bucket, PCF_BENCHMARKS["default"])
    ttm_cf     = _ttm_cashflow(statements)
    bal        = _latest_balance(statements)
    op_cf      = ttm_cf.get("operating_cash_flow")
    shares_out = bal.get("shares_outstanding")

    warnings = []
    if op_cf and op_cf > 0 and shares_out:
        cf_per_share = op_cf / shares_out
        confidence   = 61.0
    else:
        # Fallback: use FCF per share from FMP key-metrics
        cf_per_share = (ratios or {}).get("fcf_per_share")
        if cf_per_share and cf_per_share > 0:
            confidence = 52.0
            warnings.append("Using FCF per share from key metrics (cash flow statement unavailable)")
        else:
            return {"model": "pcf", "name": "Price-to-Cash-Flow", "fair_value": None,
                    "confidence": 0.0, "inputs_used": {},
                    "warnings": ["Cannot use P/CF — cash flow data unavailable from all sources"]}

    fair_value = cf_per_share * benchmark
    return {
        "model":      "pcf",
        "name":       "Price-to-Cash-Flow",
        "fair_value": round(fair_value, 2),
        "confidence": confidence,
        "inputs_used": {
            "cf_per_share":         round(cf_per_share, 2),
            "sector_pcf_benchmark": benchmark,
        },
        "warnings": warnings + [f"Uses sector average P/CF of {benchmark}×"],
    }
