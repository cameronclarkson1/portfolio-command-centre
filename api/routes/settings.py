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
            f"{BASE}/portfolios/{pid}/performance.json?start_date=2000-01-01&end_date={today}&include_sales=false",
            headers=headers, timeout=20
        )
        result["holdings_status"] = r2.status_code
        raw = r2.json()

        # Show top-level keys so we can see what fields Sharesight actually returns
        portfolio_obj = raw.get("portfolio", raw)
        result["top_level_keys"]       = list(raw.keys())
        result["portfolio_level_keys"] = list(portfolio_obj.keys())

        # ── Try shareholdings.json first (open positions only) ──────────────
        try:
            r_sh = requests.get(
                f"{BASE}/portfolios/{pid}/shareholdings.json",
                headers=headers, timeout=20
            )
            result["shareholdings_endpoint_status"] = r_sh.status_code
            if r_sh.status_code == 200:
                sh_data = r_sh.json()
                sh_list = sh_data.get("shareholdings", [])
                result["shareholdings_count"]      = len(sh_list)
                result["shareholdings_source"]     = "shareholdings.json (open positions only)"
                if sh_list:
                    result["shareholdings_field_names"] = list(sh_list[0].keys())
                    sec = sh_list[0].get("security") or {}
                    result["security_field_names"]      = list(sec.keys())
            else:
                result["shareholdings_endpoint_note"] = f"HTTP {r_sh.status_code} — falling back to performance.json"
        except Exception as e:
            result["shareholdings_endpoint_error"] = str(e)

        # ── Fall back to performance.json ─────────────────────────────────
        portfolio_obj = raw.get("portfolio", raw)
        perf_list = portfolio_obj.get("holdings", []) or portfolio_obj.get("shareholdings", [])
        result["performance_holdings_count"] = len(perf_list)
        result["performance_source"]         = "performance.json (includes closed positions)"

        if perf_list:
            result["performance_field_names"] = list(perf_list[0].keys())
            open_count = sum(
                1 for h in perf_list
                if float(h.get("quantity") or h.get("shares") or 0) > 0
                and float(h.get("value") or h.get("market_value") or 0) > 0
            )
            result["performance_open_positions"] = open_count
        else:
            result["conclusion"] = "Portfolio found but no holdings returned from performance.json either"

    except Exception as e:
        result["holdings_error"] = str(e)

    return result
