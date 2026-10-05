"""
Settings persistence — stores user preferences in api/data/settings.json.
"""

import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

router = APIRouter()

_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'settings.json')

_DEFAULTS: dict[str, Any] = {
    "risk_profile": "moderate",
    "notifications": {
        "price_alerts":      True,
        "portfolio_updates": True,
        "ai_insights":       True,
        "earnings":          False,
        "risk_alerts":       True,
        "news":              False,
    },
    "portfolio_prefs": {
        "max_sector_pct":       30,
        "cash_buffer_pct":      10,
        "rebalance_frequency":  "Monthly",
    },
    "profile": {
        "name":     "",
        "email":    "",
        "phone":    "",
        "timezone": "America/New_York",
    },
}


def _load() -> dict:
    try:
        with open(_SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _DEFAULTS.copy()


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(_SETTINGS_FILE), exist_ok=True)
    with open(_SETTINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


class SettingsPayload(BaseModel):
    risk_profile:     str | None = None
    notifications:    dict | None = None
    portfolio_prefs:  dict | None = None
    profile:          dict | None = None


@router.get("")
def get_settings():
    """Return current settings, merging saved values with defaults."""
    saved = _load()
    merged = _DEFAULTS.copy()
    merged.update({k: v for k, v in saved.items() if v is not None})
    return merged


@router.post("")
def save_settings(payload: SettingsPayload):
    """Merge the incoming partial update with the existing saved settings."""
    current = _load()
    if payload.risk_profile is not None:
        current["risk_profile"] = payload.risk_profile
    if payload.notifications is not None:
        current.setdefault("notifications", {}).update(payload.notifications)
    if payload.portfolio_prefs is not None:
        current.setdefault("portfolio_prefs", {}).update(payload.portfolio_prefs)
    if payload.profile is not None:
        current.setdefault("profile", {}).update(payload.profile)
    try:
        _save(current)
    except Exception as e:
        raise HTTPException(500, f"Could not persist settings: {e}")
    return {"ok": True}


@router.get("/sharesight-debug")
def sharesight_debug():
    """
    Diagnostic endpoint — shows exactly what Sharesight returns so we can
    spot field-name mismatches or auth failures without guessing.
    Safe to expose because the app is password-protected.
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'repo'))

    try:
        from config.api_keys import (
            SHARESIGHT_ACCESS_TOKEN, SHARESIGHT_REFRESH_TOKEN,
            SHARESIGHT_CLIENT_ID,    SHARESIGHT_PORTFOLIO_ID,
        )
    except Exception as e:
        return {"stage": "import_keys", "error": str(e)}

    result = {
        "token_present":        bool(SHARESIGHT_ACCESS_TOKEN),
        "refresh_token_present": bool(SHARESIGHT_REFRESH_TOKEN),
        "client_id_present":    bool(SHARESIGHT_CLIENT_ID),
        "portfolio_id":         SHARESIGHT_PORTFOLIO_ID or "(not set — will auto-detect)",
    }

    if not SHARESIGHT_ACCESS_TOKEN:
        result["conclusion"] = "SHARESIGHT_ACCESS_TOKEN is missing from Railway env vars"
        return result

    # Step 1 — list portfolios
    import requests
    headers = {"Authorization": f"Bearer {SHARESIGHT_ACCESS_TOKEN}"}
    BASE    = "https://api.sharesight.com/api/v2"

    try:
        r = requests.get(f"{BASE}/portfolios.json", headers=headers, timeout=15)
        result["portfolios_status"] = r.status_code
        if r.status_code == 401:
            result["conclusion"] = "Token rejected (401) — token has expired. Re-run OAuth flow and update Railway vars."
            return result
        portfolios_data = r.json()
        portfolios = portfolios_data.get("portfolios", [])
        result["portfolios_found"] = len(portfolios)
        result["portfolio_list"]   = [{"id": p["id"], "name": p.get("name")} for p in portfolios]
    except Exception as e:
        result["portfolios_error"] = str(e)
        return result

    if not portfolios:
        result["conclusion"] = "No portfolios returned — check Sharesight account has at least one portfolio"
        return result

    # Step 2 — fetch raw holdings from the first portfolio
    pid = SHARESIGHT_PORTFOLIO_ID or portfolios[0]["id"]
    result["using_portfolio_id"] = pid

    from datetime import date
    today = date.today().isoformat()
    try:
        r2 = requests.get(
            f"{BASE}/portfolios/{pid}/performance.json?start_date=2000-01-01&end_date={today}",
            headers=headers, timeout=20
        )
        result["holdings_status"] = r2.status_code
        raw = r2.json()

        # Show top-level keys so we can see what fields Sharesight actually returns
        portfolio_obj = raw.get("portfolio", raw)
        result["top_level_keys"]       = list(raw.keys())
        result["portfolio_level_keys"] = list(portfolio_obj.keys())

        shareholdings = portfolio_obj.get("shareholdings", [])
        result["shareholdings_count"] = len(shareholdings)

        # Show only field names (no values) — enough to spot field-name mismatches
        if shareholdings:
            result["all_field_names"] = list(shareholdings[0].keys())
            # Check whether each field the provider expects is actually present
            expected = ["symbol", "ticker_symbol", "quantity", "shares",
                        "cost_base", "cost_basis", "value", "market_value", "security_name"]
            result["expected_fields_present"] = {
                f: f in shareholdings[0] for f in expected
            }
        else:
            result["conclusion"] = "Portfolio found but shareholdings list is empty"

    except Exception as e:
        result["holdings_error"] = str(e)

    return result
