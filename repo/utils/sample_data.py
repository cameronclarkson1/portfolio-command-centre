"""
sample_data.py — Investor portfolio records.
Shares, avg_cost, and target_weight are the source of truth.
Current prices are overlaid by live market data on each page load.
"""

# ─── Portfolio Summary ──────────────────────────────────────────────────────────
# cash: set to 0.0 if your brokerage cash balance is not tracked here.
# portfolio_beta: rough estimate — updated automatically by the risk engine.
PORTFOLIO_SUMMARY = {
    "cash":             0.0,
    "health_score":     70,
    "num_holdings":     21,
    "portfolio_beta":   0.9,
}

# ─── Market Regime ─────────────────────────────────────────────────────────────
MARKET_REGIME = {
    "regime":       "Neutral",      # risk-on | Neutral | risk-off | crisis
    "vix":           21.4,
    "sp500_trend":  "Sideways",     # Up | Sideways | Down
    "breadth":      "Mixed",
    "summary": (
        "VIX at 21 signals moderate uncertainty. The S&P 500 is trading near its "
        "50-day moving average with mixed market breadth. Cautious buying is allowed — "
        "prefer adding to existing quality positions. Avoid initiating large new positions "
        "until a clearer trend emerges."
    ),
    "buying_rule": "🟡 Cautious buying only — prefer adds over new initiations.",
}

# ─── Market Indices ─────────────────────────────────────────────────────────────
MARKET_INDICES = [
    {"name": "S&P 500",   "value": 5_241.5,  "change_pct":  0.0048},
    {"name": "NASDAQ",    "value": 16_431.2, "change_pct":  0.0072},
    {"name": "Dow Jones", "value": 38_922.4, "change_pct":  0.0021},
    {"name": "VIX",       "value": 21.4,     "change_pct": -0.0310},
]

# ─── Sector Performance (today's % change) ─────────────────────────────────────
SECTOR_PERFORMANCE = {
    "Technology":               +0.82,
    "Healthcare":               -0.34,
    "Financials":               +0.55,
    "Consumer Staples":         -0.12,
    "Consumer Discretionary":   +0.41,
    "Energy":                   +1.24,
    "Utilities":                -0.58,
    "Industrials":              +0.19,
    "Materials":                +0.33,
    "Real Estate":              -0.89,
    "Communication Services":   +0.63,
}

# ─── Daily Decisions ───────────────────────────────────────────────────────────
# Cleared — pending new portfolio analysis
DAILY_DECISIONS = []

# ─── Risk Alerts ───────────────────────────────────────────────────────────────
# Cleared — Risk Centre now generates alerts dynamically from live portfolio data
RISK_ALERTS = []

# ─── Best Opportunities ────────────────────────────────────────────────────────
# Cleared — pending new watchlist research
OPPORTUNITIES = []

# ─── Portfolio Holdings ────────────────────────────────────────────────────────
# SOURCE OF TRUTH: edit shares and avg_cost here to update the portfolio.
# current_price is a snapshot used when live prices are unavailable.
# To add a holding: copy any entry, update ticker/name/sector/shares/avg_cost.
# To remove a holding: delete its block.
PORTFOLIO_HOLDINGS = [
    {
        "ticker": "AMZN", "name": "Amazon",               "sector": "Consumer Discretionary",
        "shares": 0.48268305, "avg_cost": 208.620, "current_price": 208.620,
    },
    {
        "ticker": "AVGO", "name": "Broadcom",             "sector": "Technology",
        "shares": 1.56727983, "avg_cost": 190.261, "current_price": 190.261,
    },
    {
        "ticker": "BABA", "name": "Alibaba Group",        "sector": "Consumer Discretionary",
        "shares": 0.84870212, "avg_cost": 115.630, "current_price": 115.630,
    },
    {
        "ticker": "BAC",  "name": "Bank of America",      "sector": "Financials",
        "shares": 9.35763340, "avg_cost":  42.931, "current_price":  42.931,
    },
    {
        "ticker": "BTG",  "name": "B2Gold Corp",          "sector": "Materials",
        "shares": 7.87403600, "avg_cost":   6.243, "current_price":   6.243,
    },
    {
        "ticker": "GOOG", "name": "Alphabet",             "sector": "Communication Services",
        "shares": 4.30615586, "avg_cost": 172.441, "current_price": 172.441,
    },
    {
        "ticker": "JNJ",  "name": "Johnson & Johnson",    "sector": "Healthcare",
        "shares": 2.09963963, "avg_cost": 169.656, "current_price": 169.656,
    },
    {
        "ticker": "KO",   "name": "Coca-Cola",            "sector": "Consumer Staples",
        "shares": 9.91349663, "avg_cost":  64.618, "current_price":  64.618,
    },
    {
        "ticker": "MA",   "name": "Mastercard",           "sector": "Financials",
        "shares": 0.09422326, "avg_cost": 520.760, "current_price": 520.760,
    },
    {
        "ticker": "MCD",  "name": "McDonald's",           "sector": "Consumer Discretionary",
        "shares": 2.24088041, "avg_cost": 272.240, "current_price": 272.240,
    },
    {
        "ticker": "META", "name": "Meta Platforms",       "sector": "Communication Services",
        "shares": 0.83024110, "avg_cost": 608.594, "current_price": 608.594,
    },
    {
        "ticker": "MO",   "name": "Altria Group",         "sector": "Consumer Staples",
        "shares": 14.93367223, "avg_cost":  53.433, "current_price":  53.433,
    },
    {
        "ticker": "MU",   "name": "Micron Technology",    "sector": "Technology",
        "shares": 0.85077788, "avg_cost": 119.123, "current_price": 119.123,
    },
    {
        "ticker": "NEM",  "name": "Newmont",              "sector": "Materials",
        "shares": 0.39273599, "avg_cost": 125.124, "current_price": 125.124,
    },
    {
        "ticker": "NVDA", "name": "NVIDIA",               "sector": "Technology",
        "shares": 3.16097096, "avg_cost": 111.428, "current_price": 111.428,
    },
    {
        "ticker": "O",    "name": "Realty Income",        "sector": "Real Estate",
        "shares": 9.95960642, "avg_cost":  52.763, "current_price":  52.763,
    },
    {
        "ticker": "SCHD", "name": "Schwab US Dividend ETF", "sector": "ETF",
        "shares": 89.69908073, "avg_cost":  27.130, "current_price":  27.130,
    },
    {
        "ticker": "V",    "name": "Visa",                 "sector": "Financials",
        "shares": 1.25863646, "avg_cost": 281.186, "current_price": 281.186,
    },
    {
        "ticker": "VOO",  "name": "Vanguard S&P 500 ETF", "sector": "ETF",
        "shares": 0.93048256, "avg_cost": 579.761, "current_price": 579.761,
    },
    {
        "ticker": "VZ",   "name": "Verizon",              "sector": "Communication Services",
        "shares": 0.74806045, "avg_cost":  39.827, "current_price":  39.827,
    },
    {
        "ticker": "WFC",  "name": "Wells Fargo",          "sector": "Financials",
        "shares": 1.25782671, "avg_cost":  78.917, "current_price":  78.917,
    },
]

# ─── Sector Exposure — computed live by portfolio.py from PORTFOLIO_HOLDINGS ───
# This is a reference snapshot only. Actual sector weights are computed live.
SECTOR_EXPOSURE = {
    "ETF":                      "~SCHD + VOO",
    "Consumer Discretionary":   "~AMZN + BABA + MCD",
    "Technology":               "~AVGO + MU + NVDA",
    "Financials":               "~BAC + MA + V + WFC",
    "Consumer Staples":         "~KO + MO",
    "Communication Services":   "~GOOG + META + VZ",
    "Healthcare":               "~JNJ",
    "Real Estate":              "~O",
    "Materials":                "~BTG + NEM",
}

# ─── Watchlist ─────────────────────────────────────────────────────────────────
# Stocks under active review with manually-researched scores and fair values.
# These are NOT current portfolio holdings.
WATCHLIST = [
    # ── Researched (scores + fair values set) ─────────────────────────────────
    {
        "ticker": "PG",  "name": "Procter & Gamble", "sector": "Consumer Staples",
        "price": 158.90, "fair_value": 175.00, "buy_below": 140.00, "upside_pct":  0.101,
        "quality": 88, "valuation": 60, "growth": 42, "momentum": 52, "risk": 86, "data_quality": 94,
        "final_score": 73, "action": "Watch",
    },
    {
        "ticker": "HD",  "name": "Home Depot",        "sector": "Consumer Discretionary",
        "price": 342.10, "fair_value": 360.00, "buy_below": 288.00, "upside_pct":  0.052,
        "quality": 86, "valuation": 52, "growth": 60, "momentum": 62, "risk": 76, "data_quality": 91,
        "final_score": 68, "action": "Watch",
    },
    # ── Research pending (use Stock Research page to score these) ─────────────
    {"ticker": "AAPL",  "name": "Apple",                  "sector": "Technology",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "MSFT",  "name": "Microsoft",              "sector": "Technology",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "AMZN",  "name": "Amazon",                 "sector": "Consumer Discretionary",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "AMD",   "name": "Advanced Micro Devices", "sector": "Technology",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "TSM",   "name": "Taiwan Semiconductor",   "sector": "Technology",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "ASML",  "name": "ASML Holding",           "sector": "Technology",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "AMAT",  "name": "Applied Materials",      "sector": "Technology",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "MA",    "name": "Mastercard",             "sector": "Financials",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "COST",  "name": "Costco",                 "sector": "Consumer Staples",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "JPM",   "name": "JPMorgan Chase",         "sector": "Financials",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "BRK.B", "name": "Berkshire Hathaway",     "sector": "Financials",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "PEP",   "name": "PepsiCo",                "sector": "Consumer Staples",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "WMT",   "name": "Walmart",                "sector": "Consumer Staples",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "LOW",   "name": "Lowe's",                 "sector": "Consumer Discretionary",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "VICI",  "name": "VICI Properties",        "sector": "Real Estate",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "PLD",   "name": "Prologis",               "sector": "Real Estate",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "AMT",   "name": "American Tower",         "sector": "Real Estate",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "DIS",   "name": "Walt Disney",            "sector": "Communication Services",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
    {"ticker": "NKE",   "name": "Nike",                   "sector": "Consumer Discretionary",
     "price": 0.0, "quality": 0, "valuation": 0, "growth": 0, "momentum": 0, "risk": 0, "data_quality": 0, "final_score": 0, "action": "Watch"},
]

# ─── Research Watchlist / Potential Buys ───────────────────────────────────────
# Stocks to research and potentially buy. No scores yet — use Stock Research page
# to run a live valuation and generate scores for any of these.
RESEARCH_WATCHLIST = [
    {"ticker": "AAPL",  "name": "Apple",                  "sector": "Technology"},
    {"ticker": "MSFT",  "name": "Microsoft",              "sector": "Technology"},
    {"ticker": "AMZN",  "name": "Amazon",                 "sector": "Consumer Discretionary"},
    {"ticker": "AMD",   "name": "Advanced Micro Devices", "sector": "Technology"},
    {"ticker": "TSM",   "name": "Taiwan Semiconductor",   "sector": "Technology"},
    {"ticker": "ASML",  "name": "ASML Holding",           "sector": "Technology"},
    {"ticker": "AMAT",  "name": "Applied Materials",      "sector": "Technology"},
    {"ticker": "MA",    "name": "Mastercard",             "sector": "Financials"},
    {"ticker": "COST",  "name": "Costco",                 "sector": "Consumer Staples"},
    {"ticker": "JPM",   "name": "JPMorgan Chase",         "sector": "Financials"},
    {"ticker": "BRK.B", "name": "Berkshire Hathaway",     "sector": "Financials"},
    {"ticker": "PEP",   "name": "PepsiCo",                "sector": "Consumer Staples"},
    {"ticker": "WMT",   "name": "Walmart",                "sector": "Consumer Staples"},
    {"ticker": "LOW",   "name": "Lowe's",                 "sector": "Consumer Discretionary"},
    {"ticker": "VICI",  "name": "VICI Properties",        "sector": "Real Estate"},
    {"ticker": "PLD",   "name": "Prologis",               "sector": "Real Estate"},
    {"ticker": "AMT",   "name": "American Tower",         "sector": "Real Estate"},
    {"ticker": "DIS",   "name": "Walt Disney",            "sector": "Communication Services"},
    {"ticker": "NKE",   "name": "Nike",                   "sector": "Consumer Discretionary"},
]

# ─── Intelligence Hub News ─────────────────────────────────────────────────────
NEWS_ITEMS = [
    {
        "ticker": "GOOGL", "name": "Alphabet", "sector": "Technology",
        "headline": "Alphabet Reports Strong Q1: Cloud Revenue Beats Estimates by 8%",
        "source": "Bloomberg", "date": "2026-05-07",
        "sentiment": "Positive", "tags": ["Earnings", "Cloud"],
        "summary": (
            "Alphabet's Q1 revenue beat consensus by 4%, driven by 28% YoY growth in Google Cloud. "
            "Operating margin expanded 180bps to 31.6%. Ad revenue remained resilient despite macro "
            "headwinds. The beat reinforces the core thesis: cloud monetisation is accelerating and "
            "margins are expanding. Position thesis is intact. Consider adding below $156 (buy-below price)."
        ),
        "impact": "Positive", "thesis": "Intact",
    },
    {
        "ticker": "ABBV", "name": "AbbVie", "sector": "Healthcare",
        "headline": "AbbVie Faces Humira Biosimilar Competition — Revenue Guidance Trimmed",
        "source": "Reuters", "date": "2026-05-06",
        "sentiment": "Negative", "tags": ["Earnings", "Guidance", "Drugs"],
        "summary": (
            "AbbVie trimmed FY26 revenue guidance by 2% due to faster-than-expected biosimilar erosion "
            "of Humira. Skyrizi and Rinvoq remain strong growth drivers but may not fully offset "
            "near-term Humira headwinds. Thesis is weakening marginally. Trimming is appropriate given "
            "the position exceeds target weight. Monitor Q2 pipeline updates before reassessing."
        ),
        "impact": "Negative", "thesis": "Weakening",
    },
    {
        "ticker": "JPM", "name": "JPMorgan Chase", "sector": "Financials",
        "headline": "Fed Holds Rates Steady — Net Interest Margin Pressure Eases for Banks",
        "source": "WSJ", "date": "2026-05-05",
        "sentiment": "Neutral", "tags": ["Macro", "Interest Rates", "Banking"],
        "summary": (
            "The Federal Reserve held rates steady, reducing near-term uncertainty for bank NIM. "
            "JPMorgan's deposit mix remains healthy and NII is expected to stabilise in H2 2026. "
            "No change to investment thesis. Hold at current weight. A rate cut in late 2026 could "
            "provide upside to book value and NIM recovery."
        ),
        "impact": "Neutral", "thesis": "Intact",
    },
    {
        "ticker": "NVDA", "name": "NVIDIA", "sector": "Technology",
        "headline": "NVIDIA Data Centre Revenue Surges 400% YoY — Valuation at Record Highs",
        "source": "CNBC", "date": "2026-05-04",
        "sentiment": "Mixed", "tags": ["Earnings", "AI", "Semiconductors"],
        "summary": (
            "NVIDIA posted extraordinary revenue growth, but the stock now trades at 45× forward revenue. "
            "Under even optimistic assumptions, fair value is ~$580. At $878, there is no margin of safety. "
            "Business quality is exceptional — valuation is not. Thesis: Avoid until valuation normalises. "
            "No action recommended. Maintain Avoid rating and monitor for a significant pullback."
        ),
        "impact": "Neutral", "thesis": "Intact",
    },
    {
        "ticker": "VZ", "name": "Verizon", "sector": "Communication Services",
        "headline": "Verizon Misses Subscriber Targets for Third Consecutive Quarter",
        "source": "FT", "date": "2026-05-03",
        "sentiment": "Negative", "tags": ["Earnings", "Dividends", "Telecom"],
        "summary": (
            "Verizon missed subscriber growth estimates for the third straight quarter. Management "
            "reduced FCF guidance, raising questions about long-term dividend sustainability. "
            "The 6.8% yield remains attractive but FCF coverage is tightening. Consider trimming "
            "the position to the 5% target weight. Thesis requires close monitoring over the next "
            "two quarters before a Sell decision is warranted."
        ),
        "impact": "Negative", "thesis": "Weakening",
    },
]
