from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date as _date
from fastapi import APIRouter, HTTPException
from services import news_service

router = APIRouter()

# Pull news for these tickers to build a market-wide feed
_MARKET_TICKERS = ["SPY", "NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN"]


@router.get("/market")
def get_market_news(limit: int = 8):
    """
    Latest market news, de-duplicated across major tickers.
    Returns up to `limit` headlines sorted newest-first.
    """
    try:
        all_news: list[dict] = []
        seen: set[str] = set()

        # Fetch from the first 4 tickers to balance coverage vs API calls
        for ticker in _MARKET_TICKERS[:4]:
            items = news_service.get_stock_news(ticker, days_back=2) or []
            for item in items:
                headline = item.get("headline", "")
                if headline and headline not in seen:
                    seen.add(headline)
                    all_news.append(item)

        all_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        return all_news[:limit]

    except Exception as e:
        raise HTTPException(500, str(e))


def _equity_holdings() -> list[dict]:
    """Portfolio holdings excluding ETFs — used for the earnings scan."""
    from utils.sample_data import PORTFOLIO_HOLDINGS
    seen: set[str] = set()
    result: list[dict] = []
    for h in PORTFOLIO_HOLDINGS:
        t = h.get("ticker", "")
        if t and t not in seen and h.get("sector") != "ETF":
            seen.add(t)
            result.append({"ticker": t, "name": h.get("name", t)})
    return result


@router.get("/earnings")
def get_portfolio_earnings():
    """Upcoming earnings dates for portfolio equity holdings, fetched in parallel."""
    holdings  = _equity_holdings()[:14]
    today_iso = _date.today().isoformat()
    all_events: list[dict] = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(news_service.get_earnings_events, h["ticker"]): h
            for h in holdings
        }
        for future in as_completed(futures, timeout=15):
            h = futures[future]
            try:
                for e in (future.result() or []):
                    if e.get("date", "") >= today_iso:
                        all_events.append({
                            "ticker":       h["ticker"],
                            "name":         h["name"],
                            "date":         e.get("date"),
                            "hour":         e.get("hour"),          # "amc" | "bmo"
                            "eps_estimate": e.get("eps_estimate"),
                        })
            except Exception:
                pass

    all_events.sort(key=lambda x: x.get("date", ""))
    return all_events[:15]
