"""
validation_utils.py — Input validation and data completeness checks.

Used by services to check whether the data returned by providers is
complete enough to trust, and to calculate completeness scores.
"""

from typing import Any


def is_valid_ticker(ticker: str) -> bool:
    """
    Basic sanity check: 1–10 characters, alphanumeric + dots/hyphens.
    Covers US tickers (MSFT), BRK.B style, and international formats.
    """
    if not isinstance(ticker, str):
        return False
    clean = ticker.strip().upper()
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    return 1 <= len(clean) <= 10 and all(c in allowed for c in clean)


def is_positive_number(value: Any) -> bool:
    """Return True if value is a real, positive number (not None, not zero, not negative)."""
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def fields_present(data: dict, required: list[str]) -> tuple[bool, list[str]]:
    """
    Check that all required keys exist and are not None/empty.

    Returns:
        (all_present: bool, missing_fields: list[str])
    """
    missing = [f for f in required if data.get(f) in (None, "", 0)]
    return len(missing) == 0, missing


def completeness_score(data: dict, expected_fields: list[str]) -> float:
    """
    Calculate what fraction of expected fields are populated.

    Returns a float between 0.0 (nothing present) and 1.0 (everything present).
    Used as one input to the overall confidence score.
    """
    if not expected_fields:
        return 1.0
    filled = sum(
        1 for f in expected_fields
        if data.get(f) not in (None, "", 0, [])
    )
    return filled / len(expected_fields)


def cross_validate(value_a: float | None, value_b: float | None, tolerance: float = 0.05) -> bool:
    """
    Check whether two values from different sources agree within tolerance.

    Example: FMP reports revenue of $100B, SEC EDGAR reports $101B.
    With tolerance=0.05 (5%), these agree → returns True.
    """
    if value_a is None or value_b is None:
        return False
    if value_a == 0 and value_b == 0:
        return True
    if value_a == 0 or value_b == 0:
        return False
    diff = abs(value_a - value_b) / max(abs(value_a), abs(value_b))
    return diff <= tolerance


# ─── Expected field lists for completeness scoring ───────────────────────────
# Services use these lists when calculating how complete a data response is.

PRICE_FIELDS = ["price", "change_pct", "volume", "market_cap"]

FUNDAMENTALS_FIELDS = [
    "revenue", "gross_profit", "operating_income", "net_income",
    "ebitda", "eps", "free_cash_flow", "total_debt", "cash",
    "shares_outstanding", "return_on_equity", "return_on_capital",
]

DCF_INPUT_FIELDS = [
    "revenue", "revenue_growth", "ebit_margin", "tax_rate",
    "depreciation", "capex", "working_capital_change",
    "free_cash_flow", "wacc", "terminal_growth",
    "shares_outstanding", "net_debt",
]

DIVIDEND_MODEL_FIELDS = [
    "dividend_per_share", "dividend_growth", "payout_ratio",
    "free_cash_flow", "cost_of_equity",
]

RELATIVE_VALUATION_FIELDS = [
    "forward_pe", "ev_ebitda", "ev_sales", "peg_ratio",
    "revenue_growth", "ebitda_margin", "roic", "debt_to_equity",
]

MACRO_FIELDS = [
    "fed_funds_rate", "treasury_10y", "treasury_2y",
    "cpi_yoy", "unemployment",
]
