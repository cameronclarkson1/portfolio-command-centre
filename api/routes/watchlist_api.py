"""
watchlist_api.py — /api/watchlist/refresh endpoint.

Accepts a list of tickers and returns enriched scoring data for each:
valuation, scores (Quality/Growth/Valuation/Safety), and live price.
All tasks run in parallel to minimise latency.
"""

import json
import os
from fastapi import APIRouter
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.sample_data import WATCHLIST as DEFAULT_WATCHLIST

_WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "watchlist.json")


def _default_watchlist() -> list:
    """
    Convert sample_data.WATCHLIST into the WatchlistItem shape the frontend expects.
    Used as the permanent fallback when watchlist.json doesn't exist or is empty.
    Railway's filesystem is ephemeral (wiped on every deploy), so defaults must
    live in code, not in a file.
    """
    items = []
    for w in DEFAULT_WATCHLIST:
        upside_pct = w.get("upside_pct", 0.0) or 0.0
        items.append({
            "symbol":         w["ticker"],
            "name":           w.get("name", w["ticker"]),
            "price":          w.get("price", 0.0),
            "change":         0.0,
            "changePercent":  0.0,
            "fairValue":      w.get("fair_value", 0.0),
            "rating":         w.get("action", "Watch"),
            "upside":         round(upside_pct * 100, 1),
            "safetyScore":    w.get("risk", 0),
            "sparkline":      [],
            "finalScore":     w.get("final_score") or None,
            "qualityScore":   w.get("quality")     or None,
            "growthScore":    w.get("growth")      or None,
            "valuationScore": w.get("valuation")   or None,
        })
    return items


def _read_watchlist() -> list:
    """
    Read saved watchlist from disk and merge with the coded defaults.

    The defaults list is always the floor: every ticker in DEFAULT_WATCHLIST
    will appear in the response even if it was missing from the saved file.
    Saved items overlay defaults (preserving refreshed scores/prices).
    User-added tickers (not in defaults) are appended at the end.

    This makes the list resilient to stale saves from old browser code that
    only knew about 2 tickers — those saves are merged into the full 33.
    """
    defaults = _default_watchlist()

    try:
        if os.path.exists(_WATCHLIST_FILE):
            with open(_WATCHLIST_FILE) as f:
                data = json.load(f)
            if data:
                saved_map = {item["symbol"]: item for item in data}
                default_symbols = {d["symbol"] for d in defaults}

                # Start with defaults, overlay any saved data (scores, prices) on top
                merged = [
                    saved_map.get(d["symbol"], d)
                    for d in defaults
                ]
                # Append user-added tickers not in defaults
                extras = [item for item in data if item["symbol"] not in default_symbols]
                return merged + extras
    except Exception:
        pass

    return defaults

def _write_watchlist(items: list) -> None:
    os.makedirs(os.path.dirname(_WATCHLIST_FILE), exist_ok=True)
    with open(_WATCHLIST_FILE, "w") as f:
        json.dump(items, f)

from services.valuation_engine import run_valuation
from services import market_data_service, fundamentals_service
from services.scoring_service import (
    build_scoring_inputs,
    compute_scores,
    generate_investment_thesis,
)

router = APIRouter()


class RefreshRequest(BaseModel):
    tickers: list[str]


def _refresh_one(ticker: str) -> dict:
    """
    Run valuation + key ratios + financial statements in parallel for one ticker,
    then compute scores. Returns a flat dict ready to send to the frontend.
    """
    ticker = ticker.strip().upper()

    tasks = {
        "price":      lambda: market_data_service.get_live_price(ticker),
        "valuation":  lambda: run_valuation(ticker),
        "ratios":     lambda: fundamentals_service.get_key_ratios(ticker),
        "statements": lambda: fundamentals_service.get_financial_statements(ticker),
    }

    results: dict = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        future_map = {pool.submit(fn): key for key, fn in tasks.items()}
        for future in as_completed(future_map, timeout=45):
            key = future_map[future]
            try:
                results[key] = future.result()
            except Exception:
                results[key] = None

    val        = results.get("valuation")  or {}
    ratios     = results.get("ratios")     or {}
    statements = results.get("statements") or {}
    price_data = results.get("price")      or {}

    price = price_data.get("price") or val.get("price") or 0.0

    # Extract margins from statement
    margins = None
    income  = (statements.get("income") or [])
    if income:
        latest  = income[0] or {}
        revenue = latest.get("revenue") or 0
        if revenue:
            gross   = latest.get("gross_profit") or 0
            op      = latest.get("operating_income") or 0
            net_i   = latest.get("net_income") or 0
            margins = {
                "gross":     round(gross / revenue * 100, 1) if gross else None,
                "operating": round(op    / revenue * 100, 1) if op    else None,
                "net":       round(net_i / revenue * 100, 1) if net_i else None,
            }

    confidence = val.get("overall_confidence")

    d = build_scoring_inputs(
        ratios       = ratios,
        margins      = margins,
        statements   = statements,
        income_series= None,
        price        = price,
        valuation    = val,
    )
    scores = compute_scores(d, confidence)

    return {
        "ticker":     ticker,
        "price":      round(price, 2) if price else None,
        "change_pct": price_data.get("change_pct"),
        "fair_value": round(val.get("fair_value_base", 0), 2) if val.get("fair_value_base") else None,
        "upside_pct": val.get("upside_pct"),
        "scores":     scores,
        "error":      None,
    }


@router.post("/refresh")
def refresh_watchlist(body: RefreshRequest):
    """
    Refresh scores and prices for a list of watchlist tickers.
    Processes up to 5 tickers in parallel (each with its own sub-pool).
    """
    tickers = [t.strip().upper() for t in body.tickers if t.strip()][:20]

    items   = [None] * len(tickers)

    with ThreadPoolExecutor(max_workers=5) as pool:
        future_map = {pool.submit(_refresh_one, t): i for i, t in enumerate(tickers)}
        for future in as_completed(future_map, timeout=60):
            idx = future_map[future]
            try:
                items[idx] = future.result()
            except Exception as e:
                items[idx] = {
                    "ticker":     tickers[idx],
                    "price":      None,
                    "change_pct": None,
                    "fair_value": None,
                    "upside_pct": None,
                    "scores":     None,
                    "error":      str(e),
                }

    # Fill any timeouts
    for i, item in enumerate(items):
        if item is None:
            items[i] = {
                "ticker":     tickers[i],
                "price":      None,
                "change_pct": None,
                "fair_value": None,
                "upside_pct": None,
                "scores":     None,
                "error":      "timeout",
            }

    return {"items": items}


class WatchlistSaveRequest(BaseModel):
    items: list


@router.get("/items")
def get_watchlist_items():
    return {"items": _read_watchlist()}


@router.post("/items")
def save_watchlist_items(body: WatchlistSaveRequest):
    _write_watchlist(body.items)
    return {"ok": True, "count": len(body.items)}
