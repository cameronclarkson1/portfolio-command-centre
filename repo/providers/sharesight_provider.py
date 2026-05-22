"""
sharesight_provider.py — Fetch real portfolio holdings from Sharesight.

Authentication:
  Sharesight uses OAuth 2.0. Run the one-time setup by visiting:
    http://localhost:8000/auth/sharesight/start
  Your tokens are then saved automatically to repo/.env.

Main function:
  get_holdings()  →  list of holdings in our standard format, ready
                     to drop into the portfolio route in place of sample_data.py
"""

import os
import requests
from datetime import datetime, timezone

from config.api_keys import (
    SHARESIGHT_CLIENT_ID,
    SHARESIGHT_CLIENT_SECRET,
    SHARESIGHT_ACCESS_TOKEN,
    SHARESIGHT_REFRESH_TOKEN,
    SHARESIGHT_PORTFOLIO_ID,
)
from utils.logging_utils import get_logger, log_provider_call

log = get_logger(__name__)

_BASE      = "https://api.sharesight.com/api/v2"
_TOKEN_URL = "https://api.sharesight.com/oauth2/token"
_TIMEOUT   = 15

# Path to repo/.env — used when saving refreshed tokens
_REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ENV_PATH = os.path.join(_REPO_DIR, ".env")

# Sector lookup built from sample_data — Sharesight doesn't provide sectors
try:
    from utils.sample_data import PORTFOLIO_HOLDINGS as _SNAPSHOT
    _SECTOR_MAP: dict[str, str] = {h["ticker"]: h["sector"] for h in _SNAPSHOT}
    _NAME_MAP:   dict[str, str] = {h["ticker"]: h["name"]   for h in _SNAPSHOT}
except Exception:
    _SECTOR_MAP = {}
    _NAME_MAP   = {}


# ── Token management ──────────────────────────────────────────────────────────

def _update_env(key: str, value: str) -> None:
    """Write a single key=value line to repo/.env without touching other keys."""
    if not os.path.exists(_ENV_PATH):
        with open(_ENV_PATH, "w") as f:
            f.write(f"{key}={value}\n")
        return

    with open(_ENV_PATH) as f:
        lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}\n")

    with open(_ENV_PATH, "w") as f:
        f.writelines(lines)


def _refresh_access_token() -> str:
    """
    Use the refresh token to get a new access token from Sharesight.
    Saves the new tokens to repo/.env so they persist across restarts.
    Returns the new access token, or raises if refresh fails.
    """
    if not SHARESIGHT_REFRESH_TOKEN:
        raise RuntimeError(
            "No Sharesight refresh token found. "
            "Visit http://localhost:8000/auth/sharesight/start to connect."
        )

    log.info("Sharesight: refreshing access token")
    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type":    "refresh_token",
            "refresh_token": SHARESIGHT_REFRESH_TOKEN,
            "client_id":     SHARESIGHT_CLIENT_ID,
            "client_secret": SHARESIGHT_CLIENT_SECRET,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    tokens = resp.json()

    new_access  = tokens["access_token"]
    new_refresh = tokens.get("refresh_token", SHARESIGHT_REFRESH_TOKEN)

    _update_env("SHARESIGHT_ACCESS_TOKEN",  new_access)
    _update_env("SHARESIGHT_REFRESH_TOKEN", new_refresh)

    # Reload so the module-level variables pick up the new values
    import importlib
    import config.api_keys as _keys
    importlib.reload(_keys)

    log.info("Sharesight: token refreshed successfully")
    return new_access


def _get_valid_token() -> str:
    """Return a working access token, refreshing if needed."""
    if not SHARESIGHT_ACCESS_TOKEN:
        raise RuntimeError(
            "Sharesight is not connected. "
            "Visit http://localhost:8000/auth/sharesight/start to set it up."
        )
    return SHARESIGHT_ACCESS_TOKEN


def _api_get(path: str) -> dict:
    """
    Make an authenticated GET request to the Sharesight API.
    Automatically retries once with a refreshed token on 401.
    """
    token = _get_valid_token()
    url   = f"{_BASE}{path}"
    log_provider_call(log, "sharesight", url)

    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=_TIMEOUT)

    # Token expired — refresh and retry once
    if resp.status_code == 401:
        log.warning("Sharesight: 401 received, attempting token refresh")
        token = _refresh_access_token()
        resp  = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=_TIMEOUT)

    resp.raise_for_status()
    return resp.json()


# ── Public functions ──────────────────────────────────────────────────────────

def get_portfolios() -> list[dict]:
    """
    Return all portfolios on the Sharesight account.
    Each item has: id, name, currency.
    """
    data = _api_get("/portfolios.json")
    portfolios = data.get("portfolios", [])
    return [
        {
            "id":       p["id"],
            "name":     p.get("name", ""),
            "currency": p.get("currency", ""),
        }
        for p in portfolios
    ]


def get_holdings(portfolio_id: int = None) -> list[dict]:
    """
    Fetch current holdings from Sharesight and return them in our
    standard format so they slot straight into the portfolio route.

    Each item:
      ticker, name, sector, shares, avg_cost, current_price

    Falls back to SHARESIGHT_PORTFOLIO_ID from .env if portfolio_id not given.
    Returns [] if Sharesight is not connected or returns no data.
    """
    pid = portfolio_id or SHARESIGHT_PORTFOLIO_ID
    if not pid:
        # Auto-select the first portfolio
        portfolios = get_portfolios()
        if not portfolios:
            log.warning("Sharesight: no portfolios found on account")
            return []
        pid = portfolios[0]["id"]
        _update_env("SHARESIGHT_PORTFOLIO_ID", str(pid))
        log.info(f"Sharesight: auto-selected portfolio id={pid}")

    # performance.json includes shareholdings and is available on all plans
    from datetime import date
    today    = date.today().isoformat()
    data     = _api_get(f"/portfolios/{pid}/performance.json?start_date=2000-01-01&end_date={today}")
    portfolio = data.get("portfolio", data)
    raw_list  = portfolio.get("shareholdings", [])

    if not raw_list:
        log.warning(f"Sharesight: portfolio {pid} returned no shareholdings")
        return []

    holdings = []
    for h in raw_list:
        # Sharesight may append the exchange code: "AAPL.XNAS" → "AAPL"
        raw_symbol = str(h.get("symbol") or h.get("ticker_symbol") or "")
        ticker     = raw_symbol.split(".")[0].upper()
        if not ticker:
            continue

        quantity = float(h.get("quantity") or h.get("shares") or 0)
        if quantity <= 0:
            continue

        # Sharesight provides total cost_basis; derive per-share avg
        total_cost = float(h.get("cost_base") or h.get("cost_basis") or 0)
        avg_cost   = round(total_cost / quantity, 4) if total_cost else 0.0

        # Use Sharesight's market value for a snapshot current price
        market_val    = float(h.get("value") or h.get("market_value") or 0)
        current_price = round(market_val / quantity, 4) if market_val and quantity else avg_cost

        holdings.append({
            "ticker":        ticker,
            "name":          h.get("security_name") or _NAME_MAP.get(ticker, ticker),
            "sector":        _SECTOR_MAP.get(ticker, "Unknown"),
            "shares":        quantity,
            "avg_cost":      avg_cost,
            "current_price": current_price,
        })

    log.info(f"Sharesight: loaded {len(holdings)} holdings from portfolio {pid}")
    return holdings
