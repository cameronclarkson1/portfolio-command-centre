from fastapi import APIRouter, HTTPException, Query
from services.valuation_engine import run_valuation

router = APIRouter()


@router.get("/{ticker}")
def get_valuation(ticker: str, price: float = Query(None)):
    """
    Run the full 9-model valuation engine for a ticker.
    Pass an optional live price to skip an extra market-data fetch.
    Returns fair value range, upside %, confidence, and model details.
    """
    ticker = ticker.strip().upper()
    try:
        result = run_valuation(ticker, price=price)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
