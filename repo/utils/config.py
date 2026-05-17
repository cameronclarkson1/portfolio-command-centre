"""
config.py — All thresholds, limits, and weights for the Portfolio Command Centre.
Change values here to tune the decision engine and risk rules.
No logic lives here — only constants.
"""

# ─── Scoring Weights ───────────────────────────────────────────────────────────
# These percentages must sum to 1.0.
SCORE_WEIGHTS = {
    "quality":      0.25,
    "valuation":    0.25,
    "growth":       0.15,
    "momentum":     0.15,
    "risk":         0.10,
    "data_quality": 0.10,
}

# ─── Decision Thresholds ───────────────────────────────────────────────────────
DECISION_THRESHOLDS = {
    # Minimum final score for each positive action
    "buy_min_score":     70,
    "add_min_score":     65,
    "hold_min_score":    50,
    "watch_min_score":   65,

    # Minimum upside to fair value required
    "buy_min_upside":    0.20,   # ≥ 20% upside needed to Buy
    "add_min_upside":    0.15,   # ≥ 15% upside needed to Add

    # Thresholds that trigger negative actions
    "trim_max_score":    55,     # Score < 55 may trigger Trim review
    "sell_max_score":    35,     # Score < 35 → Sell
    "trim_overweight":   1.10,   # Position > 110% of target weight → Trim
    "sell_max_upside":  -0.40,   # > 40% overvalued → Sell
}

# ─── Risk Management Limits ────────────────────────────────────────────────────
RISK_LIMITS = {
    "max_position_pct":    0.10,   # Hard cap: no stock > 10% of portfolio
    "min_position_pct":    0.01,   # No position smaller than 1%
    "max_sector_pct":      0.30,   # Hard cap: no sector > 30%
    "alert_sector_pct":    0.25,   # Warn when any sector exceeds 25%
    "min_cash_pct":        0.05,   # Hard floor: always keep 5% cash
    "target_cash_pct":     0.10,   # Target cash allocation
    "max_cash_pct":        0.20,   # Alert when cash > 20% (underinvested)
    "max_top3_pct":        0.30,   # Top 3 positions should not exceed 30%
    "target_beta_low":     0.80,
    "target_beta_high":    1.20,
    "alert_beta_high":     1.30,
    "alert_beta_low":      0.60,
}

# ─── Market Regime Thresholds ──────────────────────────────────────────────────
REGIME_THRESHOLDS = {
    "vix_calm":       15,    # VIX < 15 → calm, risk-on signal
    "vix_normal":     25,    # VIX 15–25 → normal
    "vix_elevated":   35,    # VIX 25–35 → elevated fear
    "vix_crisis":     45,    # VIX > 45 → crisis
    "sp500_vs_ma50":  0.95,  # S&P below 95% of its 50-day MA → bearish signal
    "sp500_vs_ma200": 0.90,  # S&P below 90% of its 200-day MA → crisis signal
}

# ─── Action Colour Map ─────────────────────────────────────────────────────────
ACTION_COLOURS = {
    "Buy":    "#00b894",   # green
    "Add":    "#0984e3",   # blue
    "Hold":   "#636e72",   # grey
    "Watch":  "#fdcb6e",   # amber
    "Trim":   "#e17055",   # orange
    "Sell":   "#d63031",   # red
    "Avoid":  "#2d3436",   # dark grey
    "Manual": "#a29bfe",   # purple
}

# ─── Sector List ───────────────────────────────────────────────────────────────
SECTORS = [
    "Technology",
    "Healthcare",
    "Financials",
    "Consumer Staples",
    "Consumer Discretionary",
    "Energy",
    "Utilities",
    "Industrials",
    "Materials",
    "Real Estate",
    "Communication Services",
]

# ─── App Meta ──────────────────────────────────────────────────────────────────
APP_NAME    = "Portfolio Command Centre"
APP_VERSION = "1.0"
APP_STAGE   = "Stage 1 — UI Shell"
CURRENCY    = "USD"
