"""
research.py — /api/research/{ticker} comprehensive stock research endpoint.

Combines valuation engine, key ratios, financial statements, analyst
actions, recent news, and earnings into a single parallel response.
The Research page calls this one endpoint instead of multiple separate calls.
"""

from fastapi import APIRouter, Query
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.valuation_engine import run_valuation
from services import market_data_service, fundamentals_service, news_service
from services.scoring_service import build_scoring_inputs, compute_scores, generate_investment_thesis
import providers.fmp_provider as fmp

router = APIRouter()


def _classify_rating(rating: str) -> str:
    """Map analyst rating strings to Buy / Hold / Sell."""
    r = (rating or "").lower()
    if any(w in r for w in ("buy", "outperform", "overweight", "strong buy", "accumulate", "add")):
        return "buy"
    if any(w in r for w in ("sell", "underperform", "underweight", "reduce", "strong sell")):
        return "sell"
    return "hold"


def _extract_income_series(statements: dict | None) -> list[dict]:
    """
    Extract annual revenue and EPS series from FMP/yfinance income statement list.
    Returns [{year, revenue_b, eps}, ...] sorted oldest → newest, max 5 years.
    """
    if not statements or not statements.get("income"):
        return []

    rows = []
    for item in statements["income"]:
        date = str(item.get("date") or item.get("period") or "")
        year = date[:4]
        if not year.isdigit():
            continue
        revenue = item.get("revenue") or item.get("totalRevenue") or 0
        eps     = item.get("eps") or item.get("epsDiluted") or 0
        if revenue:
            rows.append({
                "year":      year,
                "revenue_b": round(revenue / 1_000_000_000, 2) if revenue > 1_000_000 else round(revenue, 2),
                "eps":       round(float(eps), 2) if eps else 0,
            })

    # Deduplicate by year (keep first occurrence = most recent quarter aggregation)
    seen, unique = set(), []
    for r in rows:
        if r["year"] not in seen:
            seen.add(r["year"])
            unique.append(r)

    # Sort oldest → newest, keep last 5
    unique.sort(key=lambda r: r["year"])
    return unique[-5:]


def _get_company_name(ticker: str) -> str | None:
    """Fast yfinance lookup for company display name."""
    try:
        import yfinance as yf
        fi = yf.Ticker(ticker).fast_info
        return getattr(fi, 'short_name', None) or getattr(fi, 'long_name', None)
    except Exception:
        return None


def _extract_margins(statements: dict | None) -> dict | None:
    """Extract latest gross / operating / net margin from income statement."""
    if not statements or not statements.get("income"):
        return None

    latest = statements["income"][0]  # most recent period first
    revenue = latest.get("revenue") or 0
    if not revenue:
        return None

    gross_profit = latest.get("gross_profit") or 0
    operating    = latest.get("operating_income") or 0
    net_income   = latest.get("net_income") or 0

    return {
        "gross":     round(gross_profit / revenue * 100, 1) if gross_profit else None,
        "operating": round(operating    / revenue * 100, 1) if operating    else None,
        "net":       round(net_income   / revenue * 100, 1) if net_income   else None,
    }


@router.get("/{ticker}")
def get_research(ticker: str, price: float = Query(None)):
    """
    Full stock research for any ticker.
    Runs valuation engine + 5 service calls in parallel (30 s budget).
    Returns: valuation, ratios, income_series, margins, analyst_actions,
             recent_news, earnings.
    """
    ticker = ticker.strip().upper()

    # ── Fetch live price first (fast, 4 s timeout handled by market_data_service)
    change_pct = 0.0
    if price is None:
        try:
            pd = market_data_service.get_live_price(ticker)
            if pd and pd.get("price"):
                price      = pd["price"]
                change_pct = pd.get("change_pct", 0.0) or 0.0
        except Exception:
            pass

    # ── Parallel fetch of all research data ───────────────────────────────────
    results: dict = {}

    tasks = {
        "valuation":          lambda: run_valuation(ticker, price=price),
        "ratios":             lambda: fundamentals_service.get_key_ratios(ticker),
        "statements":         lambda: fundamentals_service.get_financial_statements(ticker),
        "analyst_consensus":  lambda: fmp.get_analyst_grades(ticker, limit=1),
        "recent_news":        lambda: news_service.get_stock_news(ticker, days_back=30),
        "earnings":           lambda: news_service.get_earnings_events(ticker),
        "company_name":       lambda: _get_company_name(ticker),
        "company_profile":    lambda: fmp.get_company_profile(ticker),
    }

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(fn): key for key, fn in tasks.items()}
        for future in as_completed(future_map, timeout=45):
            key = future_map[future]
            try:
                results[key] = future.result()
            except Exception:
                results[key] = None

    # ── Post-process analyst consensus (FMP now returns monthly aggregates) ──────
    consensus_list = results.get("analyst_consensus") or []
    latest = consensus_list[0] if consensus_list else {}
    buy_count  = latest.get("buy",  0)
    hold_count = latest.get("hold", 0)
    sell_count = latest.get("sell", 0)
    avg_target = None   # price targets no longer available from FMP stable API

    # ── Post-process financial statements ────────────────────────────────────
    statements   = results.get("statements")
    income_series = _extract_income_series(statements)
    margins      = _extract_margins(statements)

    # ── Scoring ───────────────────────────────────────────────────────────────
    valuation_result = results.get("valuation")
    ratios_result    = results.get("ratios")
    confidence       = (valuation_result or {}).get("overall_confidence")

    scoring_inputs = build_scoring_inputs(
        ratios       = ratios_result,
        margins      = margins,
        statements   = statements,
        income_series= income_series,
        price        = price,
        valuation    = valuation_result,
    )
    scores = compute_scores(scoring_inputs, confidence)
    thesis = generate_investment_thesis(
        ticker    = ticker,
        price     = price,
        scores    = scores,
        ratios    = ratios_result,
        valuation = valuation_result,
        margins   = margins,
    )

    company_name    = results.get("company_name") or None
    company_profile = results.get("company_profile") or None

    return {
        "ticker":           ticker,
        "company_name":     company_name,
        "company_profile":  company_profile,
        "price":        price,
        "change_pct":   change_pct,

        # Valuation engine result (fair value low/base/high, models, confidence)
        "valuation": valuation_result,

        # Key ratios from FMP + Finnhub
        "ratios": ratios_result,

        # Income series for revenue + EPS charts
        "income_series": income_series,

        # Latest margin percentages
        "margins": margins,

        # Composite scoring across Quality / Valuation / Growth / Safety
        "scores": scores,

        # Data-driven Bull / Bear / Base / Watch investment thesis
        "investment_thesis": thesis,

        # Analyst actions summary + raw list
        "analyst_summary": {
            "buy":        buy_count,
            "hold":       hold_count,
            "sell":       sell_count,
            "total":      buy_count + hold_count + sell_count,
            "avg_target": avg_target,
        },
        "analyst_actions": [],   # individual analyst actions no longer available from FMP stable API

        # Recent news for this ticker
        "recent_news": [
            {
                "headline":     n.get("headline", ""),
                "source":       n.get("source", ""),
                "published_at": n.get("published_at", ""),
                "summary":      n.get("summary"),
                "url":          n.get("url", ""),
            }
            for n in (results.get("recent_news") or [])[:10]
        ],

        # Upcoming earnings events
        "earnings": [
            {
                "date":         e.get("date", ""),
                "hour":         e.get("hour", ""),
                "eps_estimate": e.get("eps_estimate"),
                "revenue_est":  e.get("revenue_est"),
            }
            for e in (results.get("earnings") or [])[:3]
        ],
    }
