from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, HTTPException, Query
from services import market_data_service, macro_service
import providers.yfinance_provider as yfinance_provider

router = APIRouter()


@router.get("/regime")
def get_regime():
    """VIX-based market regime: risk-on | Neutral | risk-off | crisis"""
    try:
        result = macro_service.get_market_regime()
        if result is None:
            raise HTTPException(503, "Market regime data unavailable")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/indices")
def get_indices():
    """Live values for S&P 500, NASDAQ, Dow Jones, VIX"""
    try:
        result = market_data_service.get_market_indices()
        if result is None:
            raise HTTPException(503, "Market indices unavailable")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/sectors")
def get_sectors():
    """Daily % change per sector (via sector ETFs: XLK, XLV, XLF …)"""
    try:
        result = market_data_service.get_sector_performance()
        if result is None:
            raise HTTPException(503, "Sector data unavailable")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/macro")
def get_macro():
    """Key macro indicators from FRED: fed funds rate, 10Y/2Y yields, CPI, unemployment, GDP"""
    try:
        result = macro_service.get_macro_snapshot()
        if result is None:
            raise HTTPException(503, "Macro data unavailable")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/prices")
def get_prices(tickers: str = Query(..., description="Comma-separated ticker symbols, e.g. AAPL,MSFT,TSLA")):
    """Live price + daily change for a list of tickers.
    Returns: { "AAPL": { price, change_pct, ... }, ... }
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if not ticker_list:
            raise HTTPException(400, "No tickers provided")
        result = market_data_service.get_watchlist_prices(ticker_list)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


_COMMODITIES = [
    {"symbol": "GC=F",  "name": "Gold",        "unit": "$/oz"},
    {"symbol": "CL=F",  "name": "Crude Oil",   "unit": "$/bbl"},
    {"symbol": "SI=F",  "name": "Silver",      "unit": "$/oz"},
    {"symbol": "NG=F",  "name": "Natural Gas", "unit": "$/MMBtu"},
]

_CRYPTO = [
    {"symbol": "BTC-USD", "name": "Bitcoin",  "abbrev": "BTC"},
    {"symbol": "ETH-USD", "name": "Ethereum", "abbrev": "ETH"},
    {"symbol": "SOL-USD", "name": "Solana",   "abbrev": "SOL"},
]


def _fetch_quote_safe(ticker: str) -> dict | None:
    try:
        return yfinance_provider.get_quote(ticker)
    except Exception:
        return None


@router.get("/alternatives")
def get_alternatives():
    """Live prices for commodities (gold, oil, silver, gas) and crypto (BTC, ETH, SOL)."""
    all_tickers = [c["symbol"] for c in _COMMODITIES] + [c["symbol"] for c in _CRYPTO]

    quotes: dict[str, dict | None] = {}
    with ThreadPoolExecutor(max_workers=len(all_tickers)) as pool:
        futures = {pool.submit(_fetch_quote_safe, t): t for t in all_tickers}
        for future in as_completed(futures, timeout=10):
            ticker = futures[future]
            quotes[ticker] = future.result()

    commodities_out = []
    for meta in _COMMODITIES:
        q = quotes.get(meta["symbol"])
        commodities_out.append({
            "symbol": meta["symbol"],
            "name":   meta["name"],
            "unit":   meta["unit"],
            "price":  round(q["price"], 2) if q and q.get("price") else None,
            "change": round(q["change_pct"] * 100, 2) if q and q.get("change_pct") is not None else None,
        })

    crypto_out = []
    for meta in _CRYPTO:
        q = quotes.get(meta["symbol"])
        crypto_out.append({
            "symbol": meta["abbrev"],
            "name":   meta["name"],
            "price":  round(q["price"], 2) if q and q.get("price") else None,
            "change": round(q["change_pct"] * 100, 2) if q and q.get("change_pct") is not None else None,
        })

    return {"commodities": commodities_out, "crypto": crypto_out}


_FX_PAIRS = [
    {"symbol": "EURUSD=X", "label": "EUR/USD", "decimals": 4},
    {"symbol": "USDJPY=X", "label": "USD/JPY", "decimals": 2},
    {"symbol": "GBPUSD=X", "label": "GBP/USD", "decimals": 4},
    {"symbol": "DX-Y.NYB", "label": "DXY",     "decimals": 2},
]


@router.get("/fx")
def get_fx():
    """Live FX rates: EUR/USD, USD/JPY, GBP/USD, and US Dollar Index (DXY)."""
    results: dict[str, dict | None] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_quote_safe, p["symbol"]): p for p in _FX_PAIRS}
        for future in as_completed(futures, timeout=10):
            pair = futures[future]
            results[pair["symbol"]] = future.result()

    fx_out = []
    for pair in _FX_PAIRS:
        q = results.get(pair["symbol"])
        price = q.get("price") if q else None
        change = q.get("change_pct") if q else None
        fx_out.append({
            "label":      pair["label"],
            "price":      round(price, pair["decimals"]) if price is not None else None,
            "change_pct": round(change * 100, 2)         if change is not None else None,
        })

    return {"fx": fx_out}
