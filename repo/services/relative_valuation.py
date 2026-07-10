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


# ── Sub-sector benchmark overrides ────────────────────────────────────────────
# Industry strings come from FMP company profile.  Examples:
#   "Software—Application", "Semiconductors", "Computer Hardware",
#   "Information Technology Services", "Internet Content & Information",
#   "Biotechnology", "Drug Manufacturers—General", "Medical Devices"
#
# Return value: the specific multiple to use, or None → fall back to sector avg.

def _sub_sector_benchmark(industry: str, bucket: str, model: str) -> float | None:
    """
    Look up a more precise multiple for a given sub-sector.

    model: "ev_sales" | "ev_ebitda" | "pe"
    Returns None when no sub-sector match found so the caller uses the sector default.
    """
    if not industry:
        return None
    ind = industry.lower()

    if bucket == "technology":
        if model == "ev_sales":
            if any(k in ind for k in ("software", "saas", "application", "infrastructure", "cloud")):
                return 10.0   # SaaS / software typically 8-14×
            if any(k in ind for k in ("internet content", "interactive media", "platform")):
                return 8.0    # Internet platforms 6-10×
            if any(k in ind for k in ("semiconductor", "chip")):
                return 6.5    # Semis 5-8×
            if any(k in ind for k in ("hardware", "computer hardware", "electronic equipment")):
                return 3.0    # Hardware 2-4×
            if any(k in ind for k in ("information technology services", "it services", "consulting")):
                return 2.5    # IT services 1.5-3×
        elif model == "ev_ebitda":
            if any(k in ind for k in ("software", "saas", "application", "infrastructure", "cloud")):
                return 25.0
            if any(k in ind for k in ("internet content", "interactive media", "platform")):
                return 22.0
            if any(k in ind for k in ("semiconductor", "chip")):
                return 20.0
            if any(k in ind for k in ("hardware", "computer hardware", "electronic equipment")):
                return 15.0
            if any(k in ind for k in ("information technology services", "it services", "consulting")):
                return 14.0
        elif model == "pe":
            if any(k in ind for k in ("software", "saas", "application", "infrastructure", "cloud")):
                return 35.0
            if any(k in ind for k in ("internet content", "interactive media", "platform")):
                return 30.0
            if any(k in ind for k in ("semiconductor", "chip")):
                return 28.0
            if any(k in ind for k in ("hardware", "computer hardware", "electronic equipment")):
                return 22.0
            if any(k in ind for k in ("information technology services", "it services", "consulting")):
                return 20.0

    elif bucket == "healthcare":
        if model == "ev_sales":
            if any(k in ind for k in ("biotechnology", "biotech")):
                return 8.0
            if any(k in ind for k in ("drug manufacturer", "pharmaceutical", "specialty pharma")):
                return 4.0
            if any(k in ind for k in ("medical device", "medical instrument", "medical equipment")):
                return 5.0
            if any(k in ind for k in ("health care plan", "managed care", "health insurance")):
                return 1.0
        elif model == "pe":
            if any(k in ind for k in ("biotechnology", "biotech")):
                return 38.0
            if any(k in ind for k in ("drug manufacturer", "pharmaceutical")):
                return 18.0
            if any(k in ind for k in ("medical device", "medical instrument")):
                return 28.0

    elif bucket == "communication":
        if model == "ev_sales":
            if any(k in ind for k in ("internet content", "interactive media", "platform", "social")):
                return 6.0
            if any(k in ind for k in ("telecom", "telephone", "wireless", "broadband")):
                return 2.0
            if any(k in ind for k in ("entertainment", "media", "broadcasting", "cable")):
                return 2.5
            if any(k in ind for k in ("gaming", "electronic gaming")):
                return 4.0
        elif model == "ev_ebitda":
            if any(k in ind for k in ("internet content", "interactive media", "platform", "social")):
                return 18.0
            if any(k in ind for k in ("telecom", "telephone", "wireless", "broadband")):
                return 7.0
            if any(k in ind for k in ("entertainment", "media", "broadcasting", "cable")):
                return 12.0
            if any(k in ind for k in ("gaming", "electronic gaming")):
                return 15.0
        elif model == "pe":
            if any(k in ind for k in ("internet content", "interactive media", "platform", "social")):
                return 25.0
            if any(k in ind for k in ("telecom", "telephone", "wireless", "broadband")):
                return 14.0
            if any(k in ind for k in ("entertainment", "media", "broadcasting", "cable")):
                return 20.0

    elif bucket == "consumer_discretionary":
        if model == "ev_ebitda":
            if any(k in ind for k in ("restaurant", "food service")):
                return 16.0
            if any(k in ind for k in ("auto", "automobile", "vehicle")):
                return 10.0
            if any(k in ind for k in ("luxury", "hotels", "travel", "leisure")):
                return 14.0
            if any(k in ind for k in ("retail", "specialty retail", "apparel")):
                return 12.0
        elif model == "pe":
            if any(k in ind for k in ("internet retail", "e-commerce")):
                return 35.0
            if any(k in ind for k in ("restaurant", "food service")):
                return 26.0
            if any(k in ind for k in ("auto", "automobile", "vehicle")):
                return 15.0

    return None


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


def run_pe(bucket: str, ratios: dict, statements: dict, price: float = 0, industry: str = "") -> dict:
    """P/E comparable valuation: Fair Value = TTM EPS × sector average P/E.
    Falls back to inferring EPS from the live P/E ratio when statements are unavailable."""
    sub = _sub_sector_benchmark(industry, bucket, "pe")
    benchmark = sub if sub is not None else PE_BENCHMARKS.get(bucket, PE_BENCHMARKS["default"])
    benchmark_label = f"{benchmark}× ({'sub-sector' if sub else 'sector avg'})"
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
        "inputs_used": {"eps_ttm": round(eps, 4), "pe_benchmark": benchmark},
        "warnings":   warnings + [f"Uses {benchmark_label} P/E — individual quality premium not applied"],
    }


def run_ev_ebitda(bucket: str, ratios: dict, statements: dict, industry: str = "") -> dict:
    """EV/EBITDA valuation: Implied EV = EBITDA × benchmark, then subtract net debt."""
    sub = _sub_sector_benchmark(industry, bucket, "ev_ebitda")
    benchmark = sub if sub is not None else EV_EBITDA_BENCHMARKS.get(bucket, EV_EBITDA_BENCHMARKS["default"])
    benchmark_label = f"{benchmark}× ({'sub-sector' if sub else 'sector avg'})"

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
        "warnings": [f"Uses {benchmark_label} EV/EBITDA — individual quality not adjusted"],
    }


def run_ev_sales(bucket: str, ratios: dict, statements: dict, price: float = 0, industry: str = "") -> dict:
    """EV/Sales valuation: Implied EV = Revenue × benchmark, then subtract net debt.
    Falls back to using revenue-per-share from key metrics when statements are unavailable."""
    sub = _sub_sector_benchmark(industry, bucket, "ev_sales")
    benchmark = sub if sub is not None else EV_SALES_BENCHMARKS.get(bucket, EV_SALES_BENCHMARKS["default"])
    benchmark_label = f"{benchmark}× ({'sub-sector' if sub else 'sector avg'})"

    warnings = []
    ttm        = _ttm_income(statements)
    bal        = _latest_balance(statements)
    revenue    = ttm.get("revenue")
    net_debt   = bal.get("net_debt") or 0
    shares_out = _get_shares(statements)

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
        "warnings": warnings + [f"Uses {benchmark_label} EV/Sales"],
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


def run_analyst_pt(bucket: str, val_inputs: dict) -> dict:
    """
    Analyst consensus price target valuation.

    Uses the median price target from all covering sell-side analysts.
    Median is preferred over mean — it is less distorted by outlier calls.

    Confidence scales with analyst count and the spread between high/low targets.
    Automatically excluded (fair_value = None) for uncovered tickers so it has
    zero effect on the blend for small caps with no coverage.
    """
    pt_median     = val_inputs.get("analyst_pt_median")
    pt_consensus  = val_inputs.get("analyst_pt_consensus")
    pt_high       = val_inputs.get("analyst_pt_high")
    pt_low        = val_inputs.get("analyst_pt_low")
    analyst_count = val_inputs.get("analyst_count", 0) or 0

    fair_value = pt_median or pt_consensus   # median preferred; consensus as fallback

    if not fair_value or fair_value <= 0:
        return {
            "model":       "analyst_pt",
            "name":        "Analyst Price Target Consensus",
            "fair_value":  None,
            "confidence":  0.0,
            "inputs_used": {},
            "warnings":    ["No analyst price target data available for this ticker"],
        }

    warnings = []

    # ── Confidence: base 65, adjust for coverage depth and spread ────────────
    confidence = 65.0

    if analyst_count >= 15:
        confidence += 12.0
    elif analyst_count >= 8:
        confidence += 7.0
    elif analyst_count >= 3:
        confidence += 3.0
    elif analyst_count == 0:
        confidence -= 10.0
        warnings.append("Analyst count unknown — price target coverage may be thin")

    # Spread = disagreement among analysts
    if pt_high and pt_low and fair_value > 0:
        spread = (pt_high - pt_low) / fair_value
        if spread > 0.50:
            confidence -= 12.0
            warnings.append(
                f"Wide analyst PT spread ({spread:.0%} between high and low) — "
                "significant disagreement on fair value"
            )
        elif spread > 0.30:
            confidence -= 6.0
            warnings.append(f"Moderate analyst PT spread ({spread:.0%})")

    confidence = round(min(max(confidence, 20.0), 80.0), 1)

    return {
        "model":      "analyst_pt",
        "name":       "Analyst Price Target Consensus",
        "fair_value": round(fair_value, 2),
        "confidence": confidence,
        "inputs_used": {
            "pt_median":    round(pt_median, 2)    if pt_median    else None,
            "pt_consensus": round(pt_consensus, 2) if pt_consensus else None,
            "pt_high":      round(pt_high, 2)      if pt_high      else None,
            "pt_low":       round(pt_low, 2)       if pt_low       else None,
            "analyst_count": analyst_count,
        },
        "warnings": warnings,
    }
