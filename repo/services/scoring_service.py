"""
scoring_service.py — Standalone scoring engine for the FastAPI layer.

Public API:
    build_scoring_inputs(ratios, margins, statements, income_series, price, valuation)
    compute_scores(d, confidence)
    get_rating_label(final, quality, safety, valuation)
    generate_investment_thesis(ticker, price, scores, ratios, valuation, margins)
"""

from __future__ import annotations

import math
from typing import Optional


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_valid(v) -> bool:
    if v is None:
        return False
    try:
        return not math.isnan(float(v))
    except (TypeError, ValueError):
        return False


def _safe_float(v) -> Optional[float]:
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _band(value: Optional[float], bands: list) -> Optional[float]:
    """
    Map a value to a score using ordered threshold bands.
    Returns the score for the first band whose threshold the value is below.
    Returns None if value is None/NaN.
    """
    if not _is_valid(value):
        return None
    for threshold, score in bands:
        if value < threshold:
            return float(score)
    return float(bands[-1][1])


def _weighted_avg(pairs: list) -> Optional[float]:
    """
    Weighted average of (score, weight) pairs.
    Pairs with score=None are excluded — weights re-normalise automatically.
    """
    valid = [(s, w) for s, w in pairs if _is_valid(s)]
    if not valid:
        return None
    total_w = sum(w for _, w in valid)
    total_s = sum(s * w for s, w in valid)
    return total_s / total_w


# ── Quality score ─────────────────────────────────────────────────────────────

def score_quality(d: dict) -> Optional[float]:
    """Quality score (0-100). Higher is better."""
    roic_score = _band(d.get("roic"), [
        (0.05, 5), (0.08, 25), (0.12, 50), (0.15, 70), (0.20, 85), (math.inf, 100)
    ])
    roe_score = _band(d.get("roe"), [
        (0.05, 10), (0.10, 35), (0.15, 55), (0.20, 75), (0.25, 90), (math.inf, 100)
    ])
    op_margin_score = _band(d.get("operating_margins"), [
        (0.00, 0), (0.05, 25), (0.10, 50), (0.15, 65), (0.20, 80), (0.25, 90), (math.inf, 100)
    ])
    net_margin_score = _band(d.get("net_margins"), [
        (0.00, 0), (0.03, 20), (0.05, 40), (0.08, 55), (0.10, 65), (0.15, 80), (math.inf, 100)
    ])

    fcf = d.get("free_cash_flow")
    ni  = d.get("net_income")
    if _is_valid(fcf) and _is_valid(ni) and ni != 0:
        fcf_quality_score = _band(fcf / ni, [
            (-math.inf, 0), (0.00, 5), (0.40, 30), (0.60, 50),
            (0.80, 70), (1.00, 90), (math.inf, 100)
        ])
    else:
        fcf_quality_score = None

    ni_score  = 100.0 if (_is_valid(ni)  and ni  > 0) else (0.0 if _is_valid(ni)  else None)
    fcf_score = 100.0 if (_is_valid(fcf) and fcf > 0) else (0.0 if _is_valid(fcf) else None)

    return _weighted_avg([
        (roic_score,        0.25),
        (roe_score,         0.15),
        (op_margin_score,   0.20),
        (net_margin_score,  0.15),
        (fcf_quality_score, 0.15),
        (ni_score,          0.05),
        (fcf_score,         0.05),
    ])


# ── Growth score ──────────────────────────────────────────────────────────────

def score_growth(d: dict) -> Optional[float]:
    """Growth score (0-100). Higher is better."""
    rev_growth = d.get("revenue_growth") or d.get("revenue_cagr")
    rev_score = _band(rev_growth, [
        (-math.inf, 0), (0.00, 15), (0.05, 40), (0.10, 60),
        (0.15, 80), (0.20, 92), (math.inf, 100)
    ])

    eps_growth = d.get("earnings_growth") or d.get("eps_cagr")
    eps_score = _band(eps_growth, [
        (-math.inf, 0), (0.00, 10), (0.05, 35), (0.10, 55),
        (0.15, 70), (0.20, 85), (0.25, 95), (math.inf, 100)
    ])

    fcf_cagr = d.get("fcf_cagr")
    fcf_score = _band(fcf_cagr, [
        (-math.inf, 0), (0.00, 10), (0.05, 35), (0.10, 55),
        (0.15, 75), (0.20, 90), (math.inf, 100)
    ])

    return _weighted_avg([
        (rev_score, 0.40),
        (eps_score, 0.35),
        (fcf_score, 0.25),
    ])


# ── Valuation score ───────────────────────────────────────────────────────────

def score_valuation(d: dict) -> Optional[float]:
    """
    Valuation score (0-100). Lower multiples and higher upside = higher score.
    Captures price-level risk — overvaluation hurts this score, not the Safety score.
    """
    pe = d.get("trailing_pe")
    if _is_valid(pe) and pe < 0:
        pe = None
    pe_score = _band(pe, [
        (0.01, 0), (10, 100), (15, 95), (20, 85), (25, 72), (30, 60),
        (40, 45), (60, 30), (100, 15), (math.inf, 5)
    ])

    fpe = d.get("forward_pe")
    if _is_valid(fpe) and fpe < 0:
        fpe = None
    fpe_score = _band(fpe, [
        (0.01, 0), (10, 100), (15, 95), (18, 85), (22, 72), (28, 58),
        (35, 42), (50, 25), (math.inf, 10)
    ])

    ev_ebitda = d.get("ev_to_ebitda")
    if _is_valid(ev_ebitda) and ev_ebitda < 0:
        ev_ebitda = None
    ev_ebitda_score = _band(ev_ebitda, [
        (0.01, 0), (6, 100), (10, 88), (15, 72), (20, 55),
        (25, 38), (35, 22), (math.inf, 8)
    ])

    ps = d.get("price_to_sales")
    ps_score = _band(ps, [
        (0.01, 0), (1, 100), (2, 88), (3, 72), (5, 52),
        (8, 32), (15, 15), (math.inf, 5)
    ])

    pb = d.get("price_to_book")
    if _is_valid(pb) and pb < 0:
        pb = None
    pb_score = _band(pb, [
        (0.01, 0), (1, 100), (2, 88), (3, 72), (4, 55),
        (6, 35), (10, 18), (math.inf, 8)
    ])

    ev_fcf = d.get("ev_to_fcf")
    if _is_valid(ev_fcf) and ev_fcf < 0:
        ev_fcf = None
    ev_fcf_score = _band(ev_fcf, [
        (0.01, 0), (15, 100), (20, 88), (25, 72), (30, 55),
        (40, 38), (60, 20), (math.inf, 8)
    ])

    # Upside to fair value (decimal signed: +0.30 = 30% upside, -0.30 = 30% overvalued)
    upside = d.get("upside_pct")
    upside_score = _band(upside, [
        (-math.inf, 0), (-0.25, 5), (-0.15, 15), (-0.05, 35),
        (0.05, 55), (0.15, 75), (0.30, 92), (math.inf, 100)
    ])

    return _weighted_avg([
        (pe_score,        0.20),
        (fpe_score,       0.18),
        (ev_ebitda_score, 0.17),
        (ps_score,        0.08),
        (pb_score,        0.07),
        (ev_fcf_score,    0.07),
        (upside_score,    0.23),   # upside gets a strong weight — key signal
    ])


# ── Safety score (higher = safer) ─────────────────────────────────────────────

def score_safety(d: dict) -> Optional[float]:
    """
    Safety score (0-100). Higher = lower FINANCIAL / BUSINESS risk.

    Deliberately excludes overvaluation — that belongs in score_valuation().
    Focuses on: leverage, debt serviceability, market volatility, and drawdown.

    D/E note: companies with negative equity (e.g. KO, MCD) often produce extreme
    or undefined D/E ratios. We rely on ND/EBITDA instead for those cases.
    """
    de = d.get("debt_equity")
    if _is_valid(de):
        de = de / 100.0 if de > 20 else de   # normalize providers that return as %
        # Cap at valid range — negative equity produces nonsense ratios (> 10 or < 0)
        if de < 0.0 or de > 10.0:
            de = None

    de_score = _band(de, [
        (0.00, 100), (0.50, 92), (1.00, 80), (2.00, 62),
        (3.00, 42), (5.00, 20), (math.inf, 5)
    ])

    # Net debt / EBITDA: key leverage metric, works for negative-equity companies
    nd_ebitda = d.get("net_debt_to_ebitda")
    nd_score = _band(nd_ebitda, [
        (-math.inf, 100),   # net cash position: safest
        (0.00, 100), (1.00, 92), (2.00, 80),
        (3.00, 60), (4.00, 38), (6.00, 18), (math.inf, 5)
    ])

    # Beta: market sensitivity proxy for volatility risk
    beta = d.get("beta")
    beta_score = _band(beta, [
        (0.00, 70), (0.60, 90), (0.80, 100), (1.00, 92),
        (1.20, 80), (1.50, 62), (2.00, 38), (math.inf, 15)
    ])

    # 52-week drawdown: how far from peak (higher drawdown = more risk)
    drawdown = d.get("week52_drawdown")
    drawdown_score = _band(drawdown, [
        (-math.inf, 100),   # price at or above 52w high
        (0.10, 100), (0.20, 85), (0.30, 68),
        (0.40, 48), (0.50, 28), (0.65, 10), (math.inf, 0)
    ])

    # FCF positivity: companies burning cash are riskier
    fcf = d.get("free_cash_flow")
    fcf_safety_score = None
    if _is_valid(fcf):
        fcf_safety_score = 90.0 if fcf > 0 else 20.0

    return _weighted_avg([
        (de_score,        0.20),   # reduced weight since often missing for neg-equity firms
        (nd_score,        0.35),   # increased — reliable even without equity
        (beta_score,      0.20),
        (drawdown_score,  0.15),
        (fcf_safety_score,0.10),
    ])


# ── Rating helpers ────────────────────────────────────────────────────────────

def _raw_rating(final: float) -> str:
    """7-level rating from raw final score, no overrides applied."""
    if final >= 90: return "Strong Buy"
    if final >= 75: return "Buy"
    if final >= 60: return "Accumulate"
    if final >= 45: return "Hold / Watchlist"
    if final >= 30: return "Reduce"
    if final >= 15: return "Sell"
    return "Strong Sell"


def get_rating_label(
    final:     Optional[float],
    quality:   Optional[float] = None,
    safety:    Optional[float] = None,
    valuation: Optional[float] = None,
) -> str:
    """
    7-level rating with a quality/safety override.

    High-quality, financially safe companies should not be labelled Sell/Reduce
    purely because they are expensive. Overvaluation lowers the final score,
    but the rating is capped at Hold / Watchlist for strong businesses.
    """
    if not _is_valid(final):
        return "No Rating"

    base = _raw_rating(final)

    # Override: strong quality + strong safety + expensive → cap at Hold / Watchlist
    if (
        _is_valid(quality)   and quality   > 75 and
        _is_valid(safety)    and safety    > 65 and
        _is_valid(valuation) and valuation < 35 and
        base in ("Reduce", "Sell", "Strong Sell")
    ):
        return "Hold / Watchlist"

    return base


# ── Valuation status ──────────────────────────────────────────────────────────

def _get_valuation_status(upside_pct: Optional[float], valuation_score: Optional[float]) -> str:
    """Separate valuation status label independent of the composite rating."""
    if _is_valid(upside_pct):
        if upside_pct >=  0.30: return "Deeply Undervalued"
        if upside_pct >=  0.10: return "Undervalued"
        if upside_pct >= -0.10: return "Fairly Valued"
        if upside_pct >= -0.30: return "Overvalued"
        return "Severely Overvalued"

    # Fall back to valuation score when upside_pct is missing
    if _is_valid(valuation_score):
        if valuation_score >= 70: return "Undervalued"
        if valuation_score >= 45: return "Fairly Valued"
        if valuation_score >= 25: return "Overvalued"
        return "Severely Overvalued"

    return "Unknown"


# ── Score qualifiers ──────────────────────────────────────────────────────────

def _score_qualifiers(quality, growth, valuation, safety) -> dict:
    """Map each sub-score to a plain-English one-liner."""
    def label(score):
        if not _is_valid(score): return "no data"
        if score >= 80: return "strong positive"
        if score >= 65: return "positive"
        if score >= 50: return "moderate"
        if score >= 35: return "weak"
        return "major negative"

    return {
        "quality":   label(quality),
        "growth":    label(growth),
        "valuation": label(valuation),
        "safety":    label(safety),
    }


# ── Rating explanation sentence ───────────────────────────────────────────────

def _generate_explanation(
    rating:          str,
    quality:         Optional[float],
    growth:          Optional[float],
    valuation:       Optional[float],
    safety:          Optional[float],
    confidence:      Optional[float],
    valuation_status: str,
) -> str:
    """One or two plain-English sentences explaining the rating from real data."""
    q = quality   if _is_valid(quality)   else 50.0
    g = growth    if _is_valid(growth)    else 50.0
    v = valuation if _is_valid(valuation) else 50.0
    s = safety    if _is_valid(safety)    else 50.0

    high_quality  = q >= 75
    decent_quality = q >= 55
    low_quality   = q < 40
    expensive     = v < 35
    very_expensive = v < 20
    cheap         = v >= 65
    very_cheap    = v >= 80
    safe          = s >= 65
    risky         = s < 40
    growing       = g >= 65
    stagnant      = g < 40

    if high_quality and safe and very_expensive:
        return (
            "High-quality business with strong financials, but the current price offers very limited margin "
            "of safety. Suited for watchlist or holding existing positions — not for new buying at this valuation."
        )
    if high_quality and safe and expensive:
        return (
            "Solid fundamentals and financial stability, but the stock trades at a premium. "
            "Consider waiting for a pullback before adding to the position."
        )
    if high_quality and very_cheap and safe:
        return "Rare combination of high quality, financial safety, and a significant discount to fair value — a compelling buy candidate."
    if high_quality and cheap:
        return "Strong business quality at an attractive valuation — the core investment case is positive."
    if high_quality and risky:
        return (
            "Business quality is strong, but elevated financial risk (leverage or volatility) warrants caution "
            "around position sizing."
        )
    if low_quality and expensive:
        return "Weak business fundamentals combined with a premium valuation create an unfavourable risk/reward profile."
    if risky and expensive:
        return (
            "Both valuation and balance sheet metrics are stretched. "
            "Risk/reward does not support a position at current prices."
        )
    if decent_quality and safe and stagnant:
        return (
            "Financially solid and reasonably priced, but limited growth is a key headwind. "
            "Suitable for income-focused investors; less attractive for growth mandates."
        )
    if growing and cheap:
        return "Strong growth at a reasonable valuation — a positive combination for long-term investors."
    if very_cheap and risky:
        return (
            "Attractive valuation, but financial risk is elevated. "
            "The discount may reflect real balance sheet concerns — verify leverage before committing."
        )

    # Fallback by rating
    if rating == "Strong Buy":
        return "Scores across all dimensions support a strong buy thesis — attractive risk/reward at current prices."
    if rating == "Buy":
        return "Solid fundamentals and reasonable valuation support building a position."
    if rating == "Accumulate":
        return "Positive fundamentals — consider accumulating gradually on weakness rather than all at once."
    if rating == "Hold / Watchlist":
        if expensive:
            return "Watchlisted at current valuation — wait for a pullback or improved margin of safety before adding."
        return "A balanced profile — hold existing positions and monitor for changes in fundamentals or valuation."
    if rating == "Reduce":
        return "Risk/reward has deteriorated. Consider trimming the position, especially if fundamentals continue to weaken."
    if rating == "Sell":
        return "Valuation and risk metrics do not support holding at this price — review the position."
    if rating == "Strong Sell":
        return "Weak fundamentals and poor risk/reward suggest exiting this position."
    return "See the Score Summary for the full model assessment."


# ── Build scoring inputs ──────────────────────────────────────────────────────

def build_scoring_inputs(
    ratios:       dict | None,
    margins:      dict | None,
    statements:   dict | None,
    income_series: list | None,
    price:        float | None,
    valuation:    dict | None,
) -> dict:
    """
    Map research API response fields into the dict format the scorers expect.

    Key conversions:
    - margins from the research endpoint are in % (e.g. 68.5) → divide by 100
    - ROIC/ROE from FMP are already decimal (0.28 = 28%)
    - 52-week drawdown = (52w_high - price) / 52w_high
    - upside_pct taken directly from valuation engine output (already decimal)
    """
    r  = ratios     or {}
    m  = margins    or {}
    s  = statements or {}

    d: dict = {}

    # ── Quality inputs ────────────────────────────────────────────────────────
    d["roic"] = _safe_float(r.get("roic"))
    d["roe"]  = _safe_float(r.get("roe"))

    # Margins: research endpoint returns % values → convert to decimal for scorer
    op_m = _safe_float(m.get("operating"))
    d["operating_margins"] = (op_m / 100.0) if _is_valid(op_m) else None

    net_m = _safe_float(m.get("net"))
    d["net_margins"] = (net_m / 100.0) if _is_valid(net_m) else None

    # TTM FCF and net income (sum of last 4 periods)
    cashflows = s.get("cashflow", [])
    incomes   = s.get("income",   [])

    def _ttm(lst, *fields):
        total = 0
        found = False
        for row in lst[:4]:
            for f in fields:
                v = _safe_float(row.get(f))
                if _is_valid(v):
                    total += v
                    found = True
                    break
        return total if found else None

    d["free_cash_flow"] = _ttm(cashflows, "free_cash_flow")
    d["net_income"]     = _ttm(incomes,   "net_income", "netIncome")

    # ── Growth inputs ─────────────────────────────────────────────────────────
    d["revenue_growth"] = _safe_float(r.get("revenue_growth_yoy"))

    # EPS growth derived from income series (year-on-year)
    d["earnings_growth"] = None
    if income_series and len(income_series) >= 2:
        eps_now   = _safe_float(income_series[-1].get("eps"))
        eps_prior = _safe_float(income_series[-2].get("eps"))
        if _is_valid(eps_now) and _is_valid(eps_prior) and eps_prior and eps_prior != 0:
            d["earnings_growth"] = (eps_now - eps_prior) / abs(eps_prior)

    # FCF CAGR over 3 years (quarters[0] vs quarters[3])
    d["fcf_cagr"] = None
    if len(cashflows) >= 4:
        fcf_now = _safe_float((cashflows[0] or {}).get("free_cash_flow"))
        fcf_old = _safe_float((cashflows[3] or {}).get("free_cash_flow"))
        if _is_valid(fcf_now) and _is_valid(fcf_old) and fcf_old and fcf_old > 0:
            d["fcf_cagr"] = (fcf_now / fcf_old) ** (1.0 / 3.0) - 1.0

    # ── Valuation inputs ──────────────────────────────────────────────────────
    d["trailing_pe"]    = _safe_float(r.get("pe_ratio"))
    d["forward_pe"]     = None    # not available in key ratios
    d["ev_to_ebitda"]   = _safe_float(r.get("ev_ebitda"))
    d["price_to_sales"] = _safe_float(r.get("ps_ratio"))
    d["price_to_book"]  = _safe_float(r.get("pb_ratio"))
    d["ev_to_fcf"]      = None    # not directly available

    # Upside from fair value engine (already decimal; e.g. -0.028 = 2.8% below FV)
    d["upside_pct"] = _safe_float((valuation or {}).get("upside_pct"))

    # ── Safety / Risk inputs ──────────────────────────────────────────────────
    d["debt_equity"] = _safe_float(r.get("debt_equity"))
    d["beta"]        = _safe_float(r.get("beta"))

    # Net debt / EBITDA from balance sheet + income statement
    d["net_debt_to_ebitda"] = None
    balance = s.get("balance", [])
    if balance and incomes:
        net_debt_v = _safe_float((balance[0] or {}).get("net_debt"))
        ebitda_v   = _safe_float((incomes[0]  or {}).get("ebitda"))
        if _is_valid(net_debt_v) and _is_valid(ebitda_v) and ebitda_v and ebitda_v > 0:
            d["net_debt_to_ebitda"] = net_debt_v / ebitda_v

    # 52-week drawdown: how far price has fallen from peak
    week52_high = _safe_float(r.get("52_week_high"))
    p           = _safe_float(price)
    if _is_valid(week52_high) and _is_valid(p) and week52_high and week52_high > 0:
        d["week52_drawdown"] = max(0.0, (week52_high - p) / week52_high)
    else:
        d["week52_drawdown"] = None

    return d


# ── Compute all scores ────────────────────────────────────────────────────────

def compute_scores(d: dict, confidence: float | None) -> dict:
    """
    Run all scorers and return the full scores dict.

    Final score = Quality×0.30 + Valuation×0.30 + Growth×0.20 + Safety×0.15 + Confidence×0.05
    Safety is used directly (higher = safer = better), so the formula rewards safe companies.
    Overvaluation is captured in the Valuation score, not the Safety score.
    """
    quality   = score_quality(d)
    growth    = score_growth(d)
    valuation = score_valuation(d)
    safety    = score_safety(d)

    conf_score = min(100.0, max(0.0, float(confidence))) if _is_valid(confidence) else None

    final = _weighted_avg([
        (quality,    0.30),
        (valuation,  0.30),
        (growth,     0.20),
        (safety,     0.15),   # safety used directly: higher = better
        (conf_score, 0.05),
    ])

    upside_pct        = d.get("upside_pct")
    valuation_status  = _get_valuation_status(upside_pct, valuation)
    rating            = get_rating_label(final, quality, safety, valuation)
    rating_explanation = _generate_explanation(rating, quality, growth, valuation, safety, conf_score, valuation_status)
    score_qualifiers  = _score_qualifiers(quality, growth, valuation, safety)

    return {
        "quality_score":     round(quality,    1) if _is_valid(quality)    else None,
        "growth_score":      round(growth,     1) if _is_valid(growth)     else None,
        "valuation_score":   round(valuation,  1) if _is_valid(valuation)  else None,
        "safety_score":      round(safety,     1) if _is_valid(safety)     else None,
        "confidence":        round(conf_score, 1) if _is_valid(conf_score) else None,
        "final_score":       round(final,      1) if _is_valid(final)      else None,
        "rating":            rating,
        "valuation_status":  valuation_status,
        "rating_explanation": rating_explanation,
        "score_qualifiers":  score_qualifiers,
    }


# ── Investment thesis ─────────────────────────────────────────────────────────

def generate_investment_thesis(
    ticker:    str,
    price:     float | None,
    scores:    dict,
    ratios:    dict | None,
    valuation: dict | None,
    margins:   dict | None,
) -> dict:
    """
    Generate data-driven Bull / Bear / Base case + Watch items.
    All text comes from real data — no hardcoded narratives.
    """
    r = ratios    or {}
    v = valuation or {}
    m = margins   or {}

    bull:  list[str] = []
    bear:  list[str] = []
    base:  list[str] = []
    watch: list[str] = []

    fv_base     = _safe_float(v.get("fair_value_base"))
    p           = _safe_float(price)
    upside_pct  = _safe_float(v.get("upside_pct"))

    quality_s   = _safe_float(scores.get("quality_score"))
    growth_s    = _safe_float(scores.get("growth_score"))
    valuation_s = _safe_float(scores.get("valuation_score"))
    safety_s    = _safe_float(scores.get("safety_score"))
    final_s     = _safe_float(scores.get("final_score"))
    rating      = scores.get("rating", "Hold / Watchlist")
    conf        = _safe_float(scores.get("confidence"))
    val_status  = scores.get("valuation_status", "")

    roic       = _safe_float(r.get("roic"))
    rev_growth = _safe_float(r.get("revenue_growth_yoy"))
    pe         = _safe_float(r.get("pe_ratio"))
    de         = _safe_float(r.get("debt_equity"))
    beta       = _safe_float(r.get("beta"))
    wk52_high  = _safe_float(r.get("52_week_high"))
    op_margin  = _safe_float(m.get("operating"))   # still in %
    net_margin = _safe_float(m.get("net"))

    # ── Bull case ─────────────────────────────────────────────────────────────
    if _is_valid(quality_s) and quality_s >= 70:
        roic_str = f" (ROIC {roic*100:.1f}%)" if _is_valid(roic) else ""
        bull.append(f"High-quality business with strong returns on capital{roic_str}")

    if _is_valid(rev_growth):
        if rev_growth >= 0.15:
            bull.append(f"Strong revenue growth of {rev_growth*100:.1f}% year-over-year")
        elif rev_growth >= 0.07:
            bull.append(f"Solid revenue growth of {rev_growth*100:.1f}% year-over-year")

    if _is_valid(upside_pct) and _is_valid(fv_base):
        if upside_pct >= 0.20:
            bull.append(f"Attractive {upside_pct*100:.1f}% discount to fair value estimate (${fv_base:.2f})")
        elif upside_pct >= 0.08:
            bull.append(f"Modest {upside_pct*100:.1f}% upside to fair value estimate (${fv_base:.2f})")

    if _is_valid(op_margin) and op_margin >= 20:
        bull.append(f"Strong operating margins of {op_margin:.1f}% demonstrate pricing power")

    if _is_valid(beta) and beta < 0.75:
        bull.append(f"Defensive characteristics (beta {beta:.2f}) — lower sensitivity to market swings")

    if _is_valid(safety_s) and safety_s >= 75:
        bull.append("Strong balance sheet and cash generation reduce downside risk")

    if _is_valid(pe) and 10 <= pe <= 20:
        bull.append(f"Reasonable valuation at {pe:.1f}x earnings offers an entry opportunity")

    # ── Bear case ─────────────────────────────────────────────────────────────
    if _is_valid(pe) and pe > 30:
        bear.append(f"Elevated P/E of {pe:.1f}x limits margin of safety — any earnings miss could reprice shares")

    if _is_valid(upside_pct) and _is_valid(fv_base):
        if upside_pct < -0.20:
            bear.append(f"Trading {abs(upside_pct)*100:.1f}% above fair value estimate (${fv_base:.2f}) — significant overvaluation")
        elif upside_pct < -0.05:
            bear.append(f"Trading above fair value (${fv_base:.2f}) — limited near-term margin of safety")

    if _is_valid(rev_growth) and rev_growth < 0:
        bear.append(f"Revenue declining {abs(rev_growth)*100:.1f}% year-over-year — growth thesis under pressure")
    elif _is_valid(rev_growth) and rev_growth < 0.03:
        bear.append(f"Revenue growth of {rev_growth*100:.1f}% is below inflation — watch for margin compression")

    if _is_valid(safety_s) and safety_s < 45:
        bear.append("Elevated financial risk — leverage or cash flow metrics warrant caution")

    if _is_valid(beta) and beta > 1.5:
        bear.append(f"High beta ({beta:.2f}) means the stock can fall sharply in broad market sell-offs")

    if _is_valid(wk52_high) and _is_valid(p) and wk52_high and p:
        drawdown = (wk52_high - p) / wk52_high
        if drawdown > 0.30:
            bear.append(f"Stock is {drawdown*100:.0f}% below its 52-week high — price trend working against buyers")

    if _is_valid(quality_s) and quality_s < 40:
        bear.append("Below-average business quality weakens the investment case")

    if _is_valid(net_margin) and net_margin < 5:
        bear.append(f"Thin net margins ({net_margin:.1f}%) leave little buffer against operational headwinds")

    # ── Base case ─────────────────────────────────────────────────────────────
    if _is_valid(final_s):
        base.append(f"Model rates {ticker} as {rating} with a composite score of {final_s:.0f}/100")

    if val_status:
        base.append(f"Valuation status: {val_status}")

    if _is_valid(upside_pct) and _is_valid(fv_base):
        direction = "upside" if upside_pct >= 0 else "downside"
        base.append(
            f"Base fair value of ${fv_base:.2f} implies {abs(upside_pct)*100:.1f}% {direction} from the current price"
        )

    if _is_valid(conf):
        if conf >= 70:
            base.append(f"High model confidence ({conf:.0f}%) — data coverage is strong across all models")
        elif conf >= 50:
            base.append(f"Moderate model confidence ({conf:.0f}%) — verify key inputs before sizing the position")
        else:
            base.append(f"Lower model confidence ({conf:.0f}%) — data gaps increase uncertainty; treat score as directional")

    # ── Watch items ───────────────────────────────────────────────────────────
    if _is_valid(pe) and pe > 28:
        watch.append(f"Earnings delivery — {pe:.0f}x P/E demands consistent beats; any miss risks a de-rating")

    if _is_valid(rev_growth) and 0 < rev_growth < 0.06:
        watch.append("Revenue growth deceleration — monitor next two quarters for further slowdown")

    if _is_valid(safety_s) and safety_s < 55:
        watch.append("Balance sheet — track debt repayment progress and upcoming refinancing dates")

    if _is_valid(beta) and beta > 1.3:
        watch.append(f"Macro sensitivity (beta {beta:.2f}) — size position conservatively during risk-off episodes")

    if v.get("warnings"):
        watch.append("Valuation model has data gaps — cross-check with additional sources before committing capital")

    if not watch:
        watch.append("Monitor quarterly results for any change in growth, margins, or capital allocation")

    # ── Ensure every bucket has at least one entry ────────────────────────────
    if not bull:
        if _is_valid(final_s):
            bull.append(f"Composite score of {final_s:.0f}/100 — see Score Summary for full breakdown")
        else:
            bull.append("Insufficient data to generate specific bull case — review score summary")

    if not bear:
        bear.append("No major red flags identified — standard position-sizing and stop-loss discipline applies")

    if not base:
        base.append(f"{ticker} — see Score Summary for the full model assessment")

    return {
        "bull":  bull,
        "bear":  bear,
        "base":  base,
        "watch": watch,
    }
