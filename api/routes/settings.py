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
    try:
        _save(current)
    except Exception as e:
        raise HTTPException(500, f"Could not persist settings: {e}")
    return {"ok": True}
