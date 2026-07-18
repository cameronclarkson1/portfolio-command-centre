"""
sector_model_config.py — Ground-truth expected-model map for the coverage audit.

Derived from BUCKET_WEIGHTS and _BUCKET_MODEL_EXCLUSIONS in sector_mapper.py.
PRIMARY models are the core bucket models (from BUCKET_WEIGHTS).
SECONDARY models can be added by characteristic checks but are not guaranteed.
EXCLUDED models must never appear for this bucket type.
"""

# All model keys used in valuation_engine
ALL_MODELS = {"dcf", "pe", "pb", "ddm", "pcf", "ev_sales", "ev_ebitda", "pffo", "paffo"}

# Per-bucket configuration.
# primary:  models that MUST succeed for the bucket to be considered healthy.
# secondary: models that may be added by characteristics (good if present, not required).
# excluded:  models that must NEVER run for this bucket.
SECTOR_MODEL_CONFIG: dict[str, dict] = {
    "technology": {
        "primary":   {"dcf", "ev_sales", "ev_ebitda"},
        "secondary": {"pe", "pcf", "pb"},
        "excluded":  {"pffo", "paffo", "ddm"},
    },
    "consumer_discretionary": {
        "primary":   {"dcf", "pe", "ev_ebitda"},
        "secondary": {"pcf", "ddm"},
        "excluded":  {"pffo", "paffo", "ev_sales"},
    },
    "consumer_staples": {
        "primary":   {"dcf", "pe", "ddm"},
        "secondary": {"pcf"},
        "excluded":  {"pffo", "paffo", "ev_sales"},
    },
    "financials": {
        "primary":   {"pb", "pe", "ddm"},
        "secondary": {"pcf"},
        "excluded":  {"dcf", "ev_sales", "ev_ebitda", "pffo", "paffo"},
    },
    "insurance": {
        "primary":   {"pb", "pe", "ddm"},
        "secondary": {"pcf"},
        "excluded":  {"dcf", "ev_sales", "ev_ebitda", "pffo", "paffo"},
    },
    "reit": {
        "primary":   {"pffo", "paffo", "pb"},
        "secondary": set(),
        "excluded":  {"dcf", "ev_sales", "ev_ebitda", "pe"},
    },
    "utilities": {
        "primary":   {"ddm", "pe", "ev_ebitda"},
        "secondary": {"pcf", "pb"},
        "excluded":  {"pffo", "paffo", "ev_sales"},
    },
    "energy": {
        "primary":   {"dcf", "ev_ebitda", "pcf"},
        "secondary": {"pb", "pe"},
        "excluded":  {"pffo", "paffo", "ddm", "ev_sales"},
    },
    "materials": {
        "primary":   {"ev_ebitda", "pcf", "pb"},
        "secondary": {"pe", "dcf"},
        "excluded":  {"pffo", "paffo", "ev_sales", "ddm"},
    },
    "industrials": {
        "primary":   {"dcf", "ev_ebitda", "pe"},
        "secondary": {"pcf", "pb"},
        "excluded":  {"pffo", "paffo", "ev_sales", "ddm"},
    },
    "healthcare": {
        "primary":   {"dcf", "pe", "ev_sales"},
        "secondary": {"pcf", "ddm"},
        "excluded":  {"pffo", "paffo"},
    },
    "communication": {
        "primary":   {"dcf", "ev_ebitda", "pe"},
        "secondary": {"pcf", "ddm"},
        "excluded":  {"pffo", "paffo", "ev_sales"},
    },
    "early_stage": {
        "primary":   {"ev_sales", "pcf", "pb"},
        "secondary": set(),
        "excluded":  {"pffo", "paffo", "pe", "ddm"},
    },
    "default": {
        "primary":   {"dcf", "pe", "ev_ebitda"},
        "secondary": {"pcf", "pb"},
        "excluded":  {"pffo", "paffo"},
    },
}

# Representative sample tickers per bucket for the coverage audit.
# ~5-8 tickers per sector — mix of large-cap (data-rich) and mid-cap (data risk).
BUCKET_SAMPLE_UNIVERSE: dict[str, list[tuple[str, str]]] = {
    "technology": [
        ("AAPL",  "Apple"),
        ("MSFT",  "Microsoft"),
        ("NVDA",  "NVIDIA"),
        ("ADBE",  "Adobe"),
        ("CRM",   "Salesforce"),
    ],
    "consumer_discretionary": [
        ("AMZN",  "Amazon"),
        ("MCD",   "McDonald's"),
        ("NKE",   "Nike"),
        ("LOW",   "Lowe's"),
        ("SBUX",  "Starbucks"),
    ],
    "consumer_staples": [
        ("KO",    "Coca-Cola"),
        ("PG",    "Procter & Gamble"),
        ("WMT",   "Walmart"),
        ("MO",    "Altria"),
        ("CL",    "Colgate-Palmolive"),
    ],
    "financials": [
        ("JPM",   "JPMorgan Chase"),
        ("BAC",   "Bank of America"),
        ("WFC",   "Wells Fargo"),
        ("GS",    "Goldman Sachs"),
        ("MS",    "Morgan Stanley"),
    ],
    "insurance": [
        ("BRK-B", "Berkshire Hathaway B"),
        ("AIG",   "AIG"),
        ("PRU",   "Prudential"),
        ("MET",   "MetLife"),
        ("TRV",   "Travelers"),
    ],
    "reit": [
        ("VICI",  "VICI Properties"),
        ("O",     "Realty Income"),
        ("SPG",   "Simon Property"),
        ("AMT",   "American Tower"),
        ("PLD",   "Prologis"),
    ],
    "utilities": [
        ("NEE",   "NextEra Energy"),
        ("DUK",   "Duke Energy"),
        ("SO",    "Southern Company"),
        ("D",     "Dominion Energy"),
        ("AEP",   "American Electric Power"),
    ],
    "energy": [
        ("XOM",   "Exxon Mobil"),
        ("CVX",   "Chevron"),
        ("COP",   "ConocoPhillips"),
        ("EOG",   "EOG Resources"),
        ("SLB",   "Schlumberger"),
    ],
    "materials": [
        ("LIN",   "Linde"),
        ("APD",   "Air Products"),
        ("NEM",   "Newmont"),
        ("FCX",   "Freeport-McMoRan"),
        ("PPG",   "PPG Industries"),
    ],
    "industrials": [
        ("HON",   "Honeywell"),
        ("CAT",   "Caterpillar"),
        ("UPS",   "United Parcel Service"),
        ("GE",    "GE Aerospace"),
        ("MMM",   "3M"),
    ],
    "healthcare": [
        ("JNJ",   "Johnson & Johnson"),
        ("UNH",   "UnitedHealth Group"),
        ("PFE",   "Pfizer"),
        ("ABBV",  "AbbVie"),
        ("MRK",   "Merck"),
    ],
    "communication": [
        ("GOOGL", "Alphabet"),
        ("META",  "Meta Platforms"),
        ("DIS",   "Disney"),
        ("NFLX",  "Netflix"),
        ("VZ",    "Verizon"),
    ],
}
