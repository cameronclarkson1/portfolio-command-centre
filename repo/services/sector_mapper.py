"""
sector_mapper.py — Maps company sector/industry to a valuation bucket.

Each bucket defines which 3 valuation models are most appropriate,
their weights, and the plain-English explanation shown to the user.
"""

# FMP sector strings → our internal bucket keys
SECTOR_MAP = {
    "Technology":                  "technology",
    "Consumer Cyclical":           "consumer_discretionary",
    "Consumer Defensive":          "consumer_staples",
    "Financial Services":          "financials",
    "Real Estate":                 "reit",
    "Utilities":                   "utilities",
    "Energy":                      "energy",
    "Basic Materials":             "materials",
    "Industrials":                 "industrials",
    "Healthcare":                  "healthcare",
    "Communication Services":      "communication",
    # Alternative provider names
    "Finance":                     "financials",
    "Consumer":                    "consumer_discretionary",
    "Technology & Communications": "technology",
}

# Industry keywords that override the sector mapping (checked first)
INDUSTRY_OVERRIDES = {
    "insurance":                   "insurance",
    "banks":                       "financials",
    "diversified banks":           "financials",
    "regional banks":              "financials",
    "savings":                     "financials",
    "reit":                        "reit",
    "real estate investment trust":"reit",
    "mortgage":                    "reit",
}

# Human-readable label for each bucket
BUCKET_LABELS = {
    "technology":             "Technology",
    "consumer_discretionary": "Consumer Cyclical",
    "consumer_staples":       "Consumer Staples",
    "financials":             "Banks & Financial Services",
    "insurance":              "Insurance",
    "reit":                   "Real Estate / REIT",
    "utilities":              "Utilities",
    "energy":                 "Energy",
    "materials":              "Materials",
    "industrials":            "Industrials",
    "healthcare":             "Healthcare",
    "communication":          "Communication Services",
    "early_stage":            "Early-Stage / High-Growth",
    "default":                "General",
}

# Which 3 models to run and their weights for each bucket.
# Keys must match model keys in valuation_engine._run_model().
BUCKET_WEIGHTS = {
    "technology":             {"dcf": 0.40, "ev_sales": 0.30, "ev_ebitda": 0.30},
    "consumer_discretionary": {"dcf": 0.40, "pe":       0.30, "ev_ebitda": 0.30},
    "consumer_staples":       {"dcf": 0.40, "pe":       0.35, "ddm":       0.25},
    "financials":             {"pb":  0.40, "pe":       0.35, "ddm":       0.25},
    "insurance":              {"pb":  0.40, "pe":       0.35, "ddm":       0.25},
    "reit":                   {"pffo":0.40, "paffo":    0.40, "pb":        0.20},
    "utilities":              {"ddm": 0.40, "pe":       0.30, "ev_ebitda": 0.30},
    "energy":                 {"dcf": 0.40, "ev_ebitda":0.35, "pcf":       0.25},
    "materials":              {"ev_ebitda":0.40, "pcf": 0.35, "pb":        0.25},
    "industrials":            {"dcf": 0.40, "ev_ebitda":0.35, "pe":        0.25},
    "healthcare":             {"dcf": 0.40, "pe":       0.35, "ev_sales":  0.25},
    "communication":          {"dcf": 0.40, "ev_ebitda":0.35, "pe":        0.25},
    "early_stage":            {"ev_sales":0.50, "pcf":  0.30, "pb":        0.20},
    "default":                {"dcf": 0.40, "pe":       0.30, "ev_ebitda": 0.30},
}

# Plain-English explanation shown in the app for each bucket
BUCKET_EXPLANATIONS = {
    "technology": (
        "Technology companies are valued on growth, recurring revenue, and future cash flow potential. "
        "DCF captures long-term intrinsic value, EV/Sales reflects the growth premium, "
        "and EV/EBITDA measures operating efficiency."
    ),
    "consumer_discretionary": (
        "Consumer cyclical companies are sensitive to economic cycles. "
        "DCF provides intrinsic value, P/E compares earnings power across peers, "
        "and EV/EBITDA measures operating profitability independent of capital structure."
    ),
    "consumer_staples": (
        "Consumer staples are mature, defensive businesses with reliable cash flows and dividends. "
        "DCF, P/E earnings comparison, and the Dividend Discount Model all work well for these "
        "consistent compounders."
    ),
    "financials": (
        "Banks and financial companies should not be valued using standard free cash flow DCF — "
        "debt and cash behave fundamentally differently for financial institutions. "
        "Price-to-Book reflects net asset strength, P/E captures earnings power, "
        "and DDM values the dividend income stream."
    ),
    "insurance": (
        "Insurance companies are valued on capital strength (book value), underwriting profitability (P/E), "
        "and dividend income (DDM). Standard free cash flow DCF is not appropriate as insurance cash flows "
        "are structured around claims and investment income rather than operating activity."
    ),
    "reit": (
        "This company is classified as a REIT, so a standard free cash flow DCF is not the primary "
        "valuation method. REITs have large non-cash depreciation charges that depress reported earnings "
        "and free cash flow, making them unsuitable for DCF. "
        "P/FFO (Funds From Operations) and P/AFFO (Adjusted FFO) are the industry-standard metrics. "
        "Price-to-Book provides an asset-backing floor."
    ),
    "utilities": (
        "Utilities are regulated, capital-intensive businesses with stable earnings and high dividend payouts. "
        "The Dividend Discount Model is weighted most heavily because dividends are a core part of "
        "total return. P/E and EV/EBITDA complement it for earnings and operating profitability."
    ),
    "energy": (
        "Energy companies are cyclical and commodity-driven, making earnings volatile. "
        "DCF captures long-term intrinsic value, EV/EBITDA removes capital structure differences "
        "and is a common industry metric, and Price-to-Cash-Flow reflects actual cash generation "
        "through commodity cycles."
    ),
    "materials": (
        "Materials companies are cyclical and asset-heavy. "
        "EV/EBITDA is preferred to compare operating profitability across the cycle. "
        "Price-to-Cash-Flow reflects actual cash generation, and "
        "Price-to-Book captures underlying asset value."
    ),
    "industrials": (
        "Industrial companies have relatively predictable operations and long-term earnings power. "
        "DCF captures intrinsic value, EV/EBITDA measures operating profitability, "
        "and P/E compares earnings across the sector."
    ),
    "healthcare": (
        "Mature healthcare companies are valued on earnings and cash flows (DCF and P/E). "
        "EV/Sales is included for high-growth or early-stage healthcare companies "
        "where revenue growth matters more than current profitability."
    ),
    "communication": (
        "Communication services spans media, telecom, and internet platforms. "
        "DCF captures long-term intrinsic value, EV/EBITDA measures operating profitability "
        "across varying capital structures, and P/E compares earnings power."
    ),
    "early_stage": (
        "This company shows negative earnings or negative free cash flow, indicating early-stage "
        "or high-growth status. Standard DCF and P/E are not reliable for companies without "
        "consistent profitability. EV/Sales values the revenue base, Price-to-Cash-Flow (if positive) "
        "captures cash generation, and Price-to-Book provides a floor based on asset value."
    ),
    "default": (
        "A standard valuation approach using DCF for intrinsic value, P/E for earnings comparison, "
        "and EV/EBITDA for operating profitability."
    ),
}


# Models that must never be added to certain buckets via characteristics,
# regardless of what the company data looks like.
_BUCKET_MODEL_EXCLUSIONS: dict[str, set] = {
    "reit":       {"dcf", "ev_sales", "ev_ebitda", "pe"},  # REIT GAAP earnings distorted by property gains
    "financials": {"dcf", "ev_sales", "ev_ebitda"},          # Standard DCF/EV not appropriate for banks
    "insurance":  {"dcf", "ev_sales", "ev_ebitda"},
    "early_stage": {"ddm", "pe"},                             # No stable earnings or dividends
}


def select_models(
    bucket:     str,
    ratios:     dict | None,
    statements: dict | None,
) -> dict[str, float]:
    """
    Return {model_key: weight} normalized to 1.0.

    Starts with the sector bucket's default models (P2 base), then adds
    characteristic-eligible models that aren't already in the core (P2.1).

    Characteristic checks:
      - P/E    if earnings are positive (eps_ttm > 0 or live pe_ratio > 0)
      - DDM    if company pays a dividend (dividend_yield > 0)
      - P/CF   if operating cash flow is positive
      - P/B    if equity is positive AND sector is asset-heavy

    Added models get 50% of the smallest core weight, then everything is
    renormalised.  Never adds models that are excluded for the bucket type.
    """
    core       = dict(BUCKET_WEIGHTS.get(bucket, BUCKET_WEIGHTS["default"]))
    exclusions = _BUCKET_MODEL_EXCLUSIONS.get(bucket, set())

    ratios_d     = ratios     or {}
    statements_d = statements or {}
    income   = statements_d.get("income",   [{}])
    cashflow = statements_d.get("cashflow", [{}])
    balance  = statements_d.get("balance",  [{}])

    div_yield  = ratios_d.get("dividend_yield") or 0.0
    pe_ratio   = ratios_d.get("pe_ratio")
    eps_ttm    = sum((q.get("eps") or 0) for q in income[:4])
    op_cf_ttm  = sum((q.get("operating_cash_flow") or 0) for q in cashflow[:4])
    equity     = (balance[0] if balance else {}).get("total_equity") or 0

    # asset-heavy sectors benefit from a P/B anchor
    _asset_heavy = {"energy", "materials", "industrials", "utilities"}

    candidates: dict[str, bool] = {
        "pe":  eps_ttm > 0 or bool(pe_ratio and pe_ratio > 0),
        "ddm": div_yield > 0,
        "pcf": op_cf_ttm > 0,
        "pb":  equity > 0 and bucket in _asset_heavy,
    }

    min_core_w = min(core.values()) if core else 0.10
    additions  = {
        k: min_core_w * 0.5
        for k, eligible in candidates.items()
        if eligible and k not in core and k not in exclusions
    }

    combined = {**core, **additions}
    total    = sum(combined.values())
    return {k: round(v / total, 4) for k, v in combined.items()}


def get_bucket(sector: str | None, industry: str | None = None) -> str:
    """
    Map sector and industry strings to a valuation bucket key.

    Industry overrides are checked first (more specific).
    Then sector is matched. Falls back to 'default' if nothing matches.
    """
    # Industry overrides (case-insensitive substring match)
    if industry:
        industry_lower = industry.lower()
        for keyword, bucket in INDUSTRY_OVERRIDES.items():
            if keyword in industry_lower:
                return bucket

    # Direct sector lookup
    if sector:
        bucket = SECTOR_MAP.get(sector)
        if bucket:
            return bucket
        # Partial match fallback
        sector_lower = sector.lower()
        for key, val in SECTOR_MAP.items():
            if key.lower() in sector_lower or sector_lower in key.lower():
                return val

    return "default"


def is_early_stage(ratios: dict, statements: dict | None) -> bool:
    """
    Returns True if the company should be treated as early-stage
    (negative earnings or negative free cash flow).
    """
    # Negative P/E implies negative earnings
    pe = (ratios or {}).get("pe_ratio")
    if pe is not None and pe < 0:
        return True

    # Check net income directly from statements
    income = ((statements or {}).get("income") or [{}])
    net_income_ttm = sum((q.get("net_income") or 0) for q in income[:4])
    if net_income_ttm < 0:
        return True

    return False
