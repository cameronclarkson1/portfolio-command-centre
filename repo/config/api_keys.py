"""
api_keys.py — Load API credentials from the correct source for each environment.

LOCAL (your computer):
  - Add your keys to a .env file in the frontend/ folder (copy .env.template)
  - Keys are read automatically from that file

STREAMLIT CLOUD (live website):
  - Go to your app dashboard → Settings → Secrets
  - Paste keys in TOML format:
        POLYGON_API_KEY = "your_key_here"
        FMP_API_KEY     = "your_key_here"
  - Never put real keys in any file that goes to GitHub

This module tries st.secrets first, then falls back to the .env file,
so the same code works in both environments without any changes.
"""

import os
from dotenv import load_dotenv, find_dotenv


def _get_secret(key: str, default: str = "") -> str:
    """
    Try Streamlit secrets first (Streamlit Cloud), then .env / environment variables (local).
    Returns the default if the key is not found in either place.
    """
    # 1. Try Streamlit secrets (only available when running on Streamlit Cloud)
    try:
        import streamlit as st
        value = st.secrets.get(key)
        if value:
            return str(value)
    except Exception:
        pass  # Not running on Streamlit Cloud, or secrets not configured

    # 2. Fall back to .env file / system environment variables
    load_dotenv(find_dotenv(usecwd=True))
    return os.getenv(key, default)


# ─── API Keys ─────────────────────────────────────────────────────────────────

POLYGON_API_KEY  = _get_secret("POLYGON_API_KEY")
FMP_API_KEY      = _get_secret("FMP_API_KEY")
FINNHUB_API_KEY  = _get_secret("FINNHUB_API_KEY")
FRED_API_KEY     = _get_secret("FRED_API_KEY")

# SEC EDGAR — free, no key needed. SEC policy requires a User-Agent header.
SEC_USER_AGENT = _get_secret("SEC_USER_AGENT", "PortfolioCommandCentre contact@example.com")

# GDELT — free, no key needed
GDELT_ENABLED = _get_secret("GDELT_ENABLED", "true").lower() == "true"


def available_providers() -> dict[str, bool]:
    """Return which providers have API keys configured. Used in the data audit panel."""
    return {
        "polygon":   bool(POLYGON_API_KEY),
        "fmp":       bool(FMP_API_KEY),
        "finnhub":   bool(FINNHUB_API_KEY),
        "fred":      bool(FRED_API_KEY),
        "sec_edgar": True,   # always available (free, no key)
        "gdelt":     GDELT_ENABLED,
        "yfinance":  True,   # always available (emergency fallback, no key)
    }
