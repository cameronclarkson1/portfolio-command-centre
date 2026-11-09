"""
financial_calcs.py — Pure financial calculation helpers shared across services.

Functions:
  ttm_sum(quarters, field, n) → annualised TTM sum for a single field
"""


def ttm_sum(quarters: list, field: str, n: int = 4) -> float:
    """
    Sum `field` across up to `n` quarter records, annualising when fewer than
    `n` quarters are present in the list.

    n_actual = number of records available (len of the slice), regardless of
    whether individual field values are zero.  A quarter with zero or None data
    for this field still counts as a reported quarter — only a genuinely absent
    quarter record triggers annualisation.

    Returns 0 when the list is empty or the total is zero (no data available).

    Examples:
        4 quarters available: sum returned as-is (no scale)
        3 quarters available: sum × 4/3
        2 quarters available: sum × 2
        1 quarter  available: sum × 4
    """
    items = quarters[:n]
    n_actual = len(items)
    values = [(q.get(field) or 0) for q in items]
    total = sum(values)
    if total == 0 or n_actual == 0:
        return 0
    if n_actual < n:
        return total * (n / n_actual)
    return total
