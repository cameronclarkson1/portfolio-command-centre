"""
settings.py — App-wide configuration constants.

Do NOT put API keys here. Those live in config/api_keys.py.
This file contains thresholds, URLs, TTLs, and fallback orders —
values you might tune but that are not secrets.
"""

# ─── Cache TTLs (seconds) ─────────────────────────────────────────────────────
# How long each type of data is considered "fresh" before re-fetching.

CACHE_TTL = {
    "live_price":        60,       # 1 minute — prices move constantly
    "indices":           60,       # 1 minute
    "sector_perf":      300,       # 5 minutes
    "candles_intraday": 300,       # 5 minutes
    "candles_daily":   3600,       # 1 hour — daily candles don't change much
    "fundamentals":   86400,       # 24 hours — quarterly data
    "sec_filing":     86400,       # 24 hours
    "news":             900,       # 15 minutes
    "analyst_actions":  900,       # 15 minutes
    "earnings_events": 3600,       # 1 hour
    "macro":           3600,       # 1 hour
    "yield_curve":     3600,       # 1 hour
    "event_risk":      1800,       # 30 minutes
    "valuation":       3600,       # 1 hour — recalculate after fundamentals refresh
}

# ─── Provider Base URLs ───────────────────────────────────────────────────────

POLYGON_BASE   = "https://api.polygon.io"
FMP_BASE       = "https://financialmodelingprep.com/api/v3"
FINNHUB_BASE   = "https://finnhub.io/api/v1"
FRED_BASE      = "https://api.stlouisfed.org/fred"
GDELT_BASE     = "https://api.gdeltproject.org/api/v2"
SEC_EDGAR_BASE = "https://data.sec.gov"

# ─── Fallback Priority ────────────────────────────────────────────────────────
# Services try providers in this order. First success wins.

PRICE_FALLBACK_ORDER        = ["polygon", "finnhub", "fmp", "yfinance"]
CANDLES_FALLBACK_ORDER      = ["polygon", "finnhub", "yfinance"]
FUNDAMENTALS_FALLBACK_ORDER = ["fmp", "sec_edgar", "finnhub"]
NEWS_FALLBACK_ORDER         = ["finnhub", "fmp", "gdelt"]
MACRO_FALLBACK_ORDER        = ["fred", "polygon"]

# ─── Confidence Score Weights ─────────────────────────────────────────────────
# These add up to 100. They are used in data_quality_service.py to calculate
# an overall confidence % for each piece of data.

CONFIDENCE_WEIGHTS = {
    "primary_source_ok":     40,   # primary provider worked (vs fallback)
    "data_freshness":        25,   # how recent the data is
    "fields_complete":       20,   # how many expected fields are populated
    "cross_source_validated": 15,  # figures agree across multiple sources
}

# ─── Market Regime Thresholds (VIX-based) ────────────────────────────────────

VIX_REGIMES = {
    "risk-on":  (0,   18),    # VIX < 18
    "Neutral":  (18,  25),    # 18 ≤ VIX < 25
    "risk-off": (25,  35),    # 25 ≤ VIX < 35
    "crisis":   (35, 999),    # VIX ≥ 35
}

# ─── Sector ETF Tickers ───────────────────────────────────────────────────────
# Used to fetch today's % change per sector.

SECTOR_ETFS = {
    "Technology":             "XLK",
    "Healthcare":             "XLV",
    "Financials":             "XLF",
    "Consumer Staples":       "XLP",
    "Consumer Discretionary": "XLY",
    "Energy":                 "XLE",
    "Utilities":              "XLU",
    "Industrials":            "XLI",
    "Materials":              "XLB",
    "Real Estate":            "XLRE",
    "Communication Services": "XLC",
}

# ─── Index Tickers ────────────────────────────────────────────────────────────
# Polygon uses these tickers to fetch index values.

INDEX_TICKERS = {
    "S&P 500":   "I:SPX",
    "NASDAQ":    "I:NDX",
    "Dow Jones": "I:DJI",
    "VIX":       "I:VIX",
}

# yfinance fallback tickers for indices
INDEX_TICKERS_YFINANCE = {
    "S&P 500":   "^GSPC",
    "NASDAQ":    "^IXIC",
    "Dow Jones": "^DJI",
    "VIX":       "^VIX",
}

# ─── FRED Series IDs ─────────────────────────────────────────────────────────
# Maps friendly names to official FRED series IDs.

FRED_SERIES = {
    "fed_funds_rate": "FEDFUNDS",
    "treasury_10y":   "DGS10",
    "treasury_2y":    "DGS2",
    "treasury_3m":    "DGS3MO",
    "cpi_yoy":        "CPIAUCSL",
    "unemployment":   "UNRATE",
    "gdp_growth":     "A191RL1Q225SBEA",
}

# ─── Event Classification Categories ─────────────────────────────────────────
# Used in event_detection_service.py to tag and score news events.

EVENT_CATEGORIES = [
    "Earnings",
    "Guidance Change",
    "Analyst Upgrade",
    "Analyst Downgrade",
    "Price Target Change",
    "SEC Filing",
    "Insider Buying",
    "Insider Selling",
    "Management Change",
    "Legal / Regulatory",
    "Lawsuit",
    "Product Launch",
    "M&A Activity",
    "Macro Shock",
    "Controversy",
    "Geopolitical Risk",
    "Other",
]

# ─── HTTP Request Settings ────────────────────────────────────────────────────

REQUEST_TIMEOUT = 10       # seconds before a provider call is abandoned
MAX_RETRIES     = 2        # how many times to retry a failed request
