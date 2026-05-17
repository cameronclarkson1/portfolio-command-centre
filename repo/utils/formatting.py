"""
formatting.py — Number and text formatting helpers used across all pages.
These functions ensure consistent display of currencies, percentages, and scores.
"""

from __future__ import annotations


def fmt_currency(value: float | None, decimals: int = 0) -> str:
    """Format a number as USD.  12345.6 → '$12,346'.  1500000 → '$1.5M'."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value:,.{decimals}f}"
    return f"${value:.2f}"


def fmt_pct(value: float | None, decimals: int = 1, sign: bool = True) -> str:
    """Format a decimal fraction as a percentage.  0.1234 → '+12.3%'."""
    if value is None:
        return "N/A"
    prefix = "+" if sign and value > 0 else ""
    return f"{prefix}{value * 100:.{decimals}f}%"


def fmt_score(score: float | None) -> str:
    """Round a 0–100 score to the nearest integer.  73.4 → '73'."""
    if score is None:
        return "N/A"
    return str(int(round(score)))


def score_colour(score: float | None) -> str:
    """Return a hex colour string for a 0–100 score band."""
    if score is None:
        return "#636e72"
    if score >= 70:
        return "#00b894"   # green  — strong
    if score >= 50:
        return "#fdcb6e"   # amber  — average
    return "#d63031"       # red    — weak


def action_colour(action: str) -> str:
    """Return the hex colour for a given action string."""
    from utils.config import ACTION_COLOURS
    return ACTION_COLOURS.get(action, "#636e72")


def fmt_change(value: float | None) -> str:
    """Format a percentage change with directional arrow.  0.0098 → '▲ +0.98%'."""
    if value is None:
        return "N/A"
    arrow  = "▲" if value >= 0 else "▼"
    prefix = "+" if value >= 0 else ""
    return f"{arrow} {prefix}{value * 100:.2f}%"


def fmt_weight(value: float | None) -> str:
    """Format a portfolio weight (already in %).  7.4 → '7.4%'."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def regime_colours(regime: str) -> tuple[str, str]:
    """Return (background_colour, text_colour) for a market regime string."""
    mapping = {
        "risk-on":  ("#00b894", "white"),
        "Neutral":  ("#fdcb6e", "#1a1a2e"),
        "risk-off": ("#e17055", "white"),
        "crisis":   ("#d63031", "white"),
    }
    return mapping.get(regime, ("#636e72", "white"))
