"""
gdelt_provider.py — Raw API calls to GDELT (Global Database of Events, Language, and Tone).

GDELT scans the global news in real time and classifies events by type, tone, and geography.
Used here for: detecting controversies, geopolitical risks, and unusual event volumes
around a specific company or topic.

WARNING: GDELT is noisy. It picks up everything including irrelevant mentions.
Use it only as a supplementary risk flag, not as a primary news source.

Free and open — no API key needed.
"""

import requests
from datetime import datetime, timezone

from config.settings import GDELT_BASE, REQUEST_TIMEOUT
from utils.logging_utils import get_logger, log_provider_call

log = get_logger(__name__)


def _get(endpoint: str, params: dict = None) -> dict | list:
    """Make a GET request to GDELT. No authentication required."""
    url = f"{GDELT_BASE}{endpoint}"
    resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def search_company_news(company_name: str, max_records: int = 25) -> list[dict]:
    """
    Search GDELT for recent news articles mentioning a company.

    Args:
        company_name: The company's full name or common name, e.g. "Apple" or "Microsoft"
        max_records:  Maximum number of articles to return (capped at 250 by GDELT)

    Returns a list of article dicts with: headline, url, source_country, tone, published_at

    Note: Results are noisy — always filter and validate before surfacing to users.
    """
    log_provider_call(log, "GDELT", f"/doc/doc?query={company_name[:20]}")

    try:
        data = _get("/doc/doc", params={
            "query":      f'"{company_name}"',
            "mode":       "artlist",
            "maxrecords": max_records,
            "format":     "json",
        })
    except Exception as e:
        log.warning(f"GDELT search failed for '{company_name}': {e}")
        return []

    articles = []
    for item in (data.get("articles") or []):
        articles.append({
            "headline":       item.get("title"),
            "url":            item.get("url"),
            "source_country": item.get("sourcecountry"),
            "language":       item.get("language"),
            "tone":           item.get("tone"),        # negative tone = potentially bad news
            "published_at":   item.get("seendate"),
            "provider":       "gdelt",
        })

    return articles


def get_event_tone(company_name: str) -> dict:
    """
    Get a summary of the average news tone for a company over the past few days.
    Tone ranges from very negative (-100) to very positive (+100).
    A sharp drop in tone can signal a controversy or crisis.

    Returns: {"average_tone": float, "article_count": int, "risk_flag": bool}
    """
    articles = search_company_news(company_name, max_records=50)

    if not articles:
        return {
            "average_tone":  None,
            "article_count": 0,
            "risk_flag":     False,
            "source":        "gdelt",
        }

    tones = []
    for a in articles:
        try:
            tones.append(float(a.get("tone") or 0))
        except (ValueError, TypeError):
            continue

    avg_tone = sum(tones) / len(tones) if tones else None

    # Flag as risk if average tone is below -2.0 (meaningfully negative)
    risk_flag = avg_tone is not None and avg_tone < -2.0

    return {
        "average_tone":  round(avg_tone, 2) if avg_tone is not None else None,
        "article_count": len(articles),
        "risk_flag":     risk_flag,
        "source":        "gdelt",
        "fetched_at":    datetime.now(timezone.utc).isoformat(),
    }
