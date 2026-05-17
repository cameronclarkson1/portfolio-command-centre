"""
date_utils.py — Date and time helpers used across the app.

All timestamps in the app are UTC. Display formatting converts to local
time only at the UI layer.
"""

from datetime import datetime, timedelta, timezone


def now_utc() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def is_stale(timestamp: datetime | None, ttl_seconds: int) -> bool:
    """Return True if the timestamp is older than ttl_seconds (or is None)."""
    if timestamp is None:
        return True
    if timestamp.tzinfo is None:
        # Assume UTC if no timezone info
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age_seconds = (now_utc() - timestamp).total_seconds()
    return age_seconds > ttl_seconds


def ago_str(timestamp: datetime | None) -> str:
    """
    Convert a datetime to a human-readable 'X ago' string.

    Examples: "30s ago", "4m ago", "2h ago", "3d ago", "unknown"
    """
    if timestamp is None:
        return "unknown"
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    delta = now_utc() - timestamp
    seconds = int(delta.total_seconds())

    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def to_date_str(date: datetime = None) -> str:
    """Return YYYY-MM-DD string for a datetime (defaults to today UTC)."""
    return (date or datetime.now()).strftime("%Y-%m-%d")


def n_days_ago_str(n: int) -> str:
    """Return YYYY-MM-DD string for N calendar days ago."""
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def parse_iso(iso_str: str | None) -> datetime | None:
    """
    Parse an ISO 8601 string into a datetime object.
    Returns None if the string is empty or unparseable.
    """
    if not iso_str:
        return None
    try:
        # Handle both 'Z' suffix and '+00:00' suffix
        clean = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except (ValueError, AttributeError):
        return None


def freshness_label(timestamp: datetime | None, ttl_seconds: int) -> str:
    """
    Return a label like 'Live', 'Fresh', 'Stale', or 'Missing'.
    Used in the data audit panel to show data quality at a glance.
    """
    if timestamp is None:
        return "Missing"
    age = (now_utc() - timestamp.replace(tzinfo=timezone.utc)).total_seconds()
    if age < ttl_seconds * 0.5:
        return "Live"
    if age < ttl_seconds:
        return "Fresh"
    return "Stale"
