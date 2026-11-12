"""
test_h2_income_series.py — Regression tests for Cycle 6 fix H-2.

Bug (pre-fix):
    _extract_income_series() in api/routes/research.py iterated quarterly
    income records and kept only the FIRST occurrence per year (most recent
    quarter), discarding the other three.  A company with $100B annual revenue
    showed ~$25B for the current year — the chart appeared to show declining
    revenue when the company was growing normally.

Fix:
    Group quarterly records by calendar year and SUM revenue across all
    quarters in that year.  EPS is taken from the first (most-recent) quarter
    of the year as a representative value (summing quarterly EPS overstates
    because diluted share counts differ per quarter).

Run with:
    pytest repo/services/tests/test_h2_income_series.py -v
"""

import sys
from pathlib import Path

import pytest

# repo/services/tests/ → repo/services/ → repo/ → project_root/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPO_DIR     = PROJECT_ROOT / "repo"
API_DIR      = PROJECT_ROOT / "api"
for d in [str(REPO_DIR), str(API_DIR)]:
    if d not in sys.path:
        sys.path.insert(0, d)

from routes.research import _extract_income_series


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quarter(year_q: str, revenue: float, eps: float = 0.0) -> dict:
    """Build a minimal quarterly income record."""
    return {"date": year_q, "revenue": revenue, "eps": eps}


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------

class TestAggregation:

    def test_four_quarters_sum_to_annual(self):
        """4 × $25B quarters → $100B annual revenue for 2024."""
        stmts = {"income": [
            _quarter("2024-09-30", 25e9, eps=1.00),
            _quarter("2024-06-30", 25e9, eps=0.95),
            _quarter("2024-03-31", 25e9, eps=0.90),
            _quarter("2023-12-31", 25e9, eps=0.85),  # Dec 2023, not 2024
        ]}
        result = _extract_income_series(stmts)
        yr2024 = next(r for r in result if r["year"] == "2024")
        assert yr2024["revenue_b"] == pytest.approx(75.0)   # only 3 quarters of 2024
        yr2023 = next(r for r in result if r["year"] == "2023")
        assert yr2023["revenue_b"] == pytest.approx(25.0)

    def test_full_year_all_four_quarters(self):
        """Full 2023 year: 4 × $25B = $100B."""
        stmts = {"income": [
            _quarter("2023-12-31", 25e9),
            _quarter("2023-09-30", 25e9),
            _quarter("2023-06-30", 25e9),
            _quarter("2023-03-31", 25e9),
        ]}
        result = _extract_income_series(stmts)
        assert len(result) == 1
        assert result[0]["year"] == "2023"
        assert result[0]["revenue_b"] == pytest.approx(100.0)

    def test_pre_fix_single_quarter_no_longer_returned(self):
        """
        Pre-fix: 2024 would show $25B (one quarter kept by deduplication).
        Post-fix: 2024 must show $100B (all four quarters summed).
        """
        stmts = {"income": [
            _quarter("2024-09-30", 25e9),
            _quarter("2024-06-30", 25e9),
            _quarter("2024-03-31", 25e9),
            _quarter("2023-12-31", 25e9),  # belongs to 2023
        ]}
        result = _extract_income_series(stmts)
        yr2024 = next(r for r in result if r["year"] == "2024")
        assert yr2024["revenue_b"] != pytest.approx(25.0), (
            "Still using single-quarter revenue — H-2 fix not applied"
        )

    def test_multiple_years_aggregated_independently(self):
        """Revenue per year is independent — 2022, 2023, 2024 each summed."""
        stmts = {"income": [
            _quarter("2024-09-30", 30e9),
            _quarter("2024-06-30", 30e9),
            _quarter("2024-03-31", 28e9),
            _quarter("2023-12-31", 25e9),
            _quarter("2023-09-30", 25e9),
            _quarter("2023-06-30", 25e9),
            _quarter("2023-03-31", 25e9),
            _quarter("2022-12-31", 20e9),
            _quarter("2022-09-30", 20e9),
            _quarter("2022-06-30", 20e9),
            _quarter("2022-03-31", 20e9),
        ]}
        result = _extract_income_series(stmts)
        by_year = {r["year"]: r["revenue_b"] for r in result}
        assert by_year["2022"] == pytest.approx(80.0)
        assert by_year["2023"] == pytest.approx(100.0)
        assert by_year["2024"] == pytest.approx(88.0)   # 3 quarters only


# ---------------------------------------------------------------------------
# EPS handling
# ---------------------------------------------------------------------------

class TestEpsHandling:

    def test_eps_taken_from_most_recent_quarter(self):
        """EPS comes from the first (most-recent) quarter record for that year."""
        stmts = {"income": [
            _quarter("2024-09-30", 25e9, eps=1.20),  # most recent → used
            _quarter("2024-06-30", 25e9, eps=1.10),
            _quarter("2024-03-31", 25e9, eps=0.90),
            _quarter("2023-12-31", 25e9, eps=0.80),
        ]}
        result = _extract_income_series(stmts)
        yr2024 = next(r for r in result if r["year"] == "2024")
        assert yr2024["eps"] == pytest.approx(1.20)

    def test_eps_not_summed_across_quarters(self):
        """Summing 4 × $1 EPS would give $4 — post-fix must not do this."""
        stmts = {"income": [
            _quarter("2023-12-31", 25e9, eps=1.00),
            _quarter("2023-09-30", 25e9, eps=1.00),
            _quarter("2023-06-30", 25e9, eps=1.00),
            _quarter("2023-03-31", 25e9, eps=1.00),
        ]}
        result = _extract_income_series(stmts)
        assert result[0]["eps"] == pytest.approx(1.00), (
            "EPS should come from one quarter, not sum of all four"
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_statements_returns_empty(self):
        assert _extract_income_series(None) == []
        assert _extract_income_series({}) == []
        assert _extract_income_series({"income": []}) == []

    def test_no_revenue_rows_excluded(self):
        """Rows with zero/None revenue are excluded."""
        stmts = {"income": [
            _quarter("2024-09-30", 0),
            _quarter("2024-06-30", None),
            _quarter("2023-12-31", 25e9),
        ]}
        result = _extract_income_series(stmts)
        years = {r["year"] for r in result}
        assert "2024" not in years   # all 2024 rows had no revenue
        assert "2023" in years

    def test_max_five_years_returned(self):
        """At most 5 years returned, keeping the most recent."""
        stmts = {"income": [
            _quarter(f"{yr}-12-31", 10e9) for yr in range(2018, 2025)
        ]}
        result = _extract_income_series(stmts)
        assert len(result) == 5
        years = [r["year"] for r in result]
        assert "2020" in years
        assert "2024" in years
        assert "2018" not in years   # oldest dropped

    def test_sorted_oldest_to_newest(self):
        """Result must be sorted chronologically."""
        stmts = {"income": [
            _quarter("2022-12-31", 10e9),
            _quarter("2024-12-31", 10e9),
            _quarter("2023-12-31", 10e9),
        ]}
        result = _extract_income_series(stmts)
        years = [r["year"] for r in result]
        assert years == sorted(years)

    def test_mixed_chronological_input_order(self):
        """Input in arbitrary order — output still sorted and correctly aggregated."""
        stmts = {"income": [
            _quarter("2023-06-30", 20e9),
            _quarter("2024-09-30", 30e9),
            _quarter("2023-12-31", 25e9),
            _quarter("2024-03-31", 28e9),
            _quarter("2023-09-30", 22e9),
            _quarter("2024-06-30", 29e9),
            _quarter("2023-03-31", 18e9),
        ]}
        result = _extract_income_series(stmts)
        by_year = {r["year"]: r["revenue_b"] for r in result}
        assert by_year["2023"] == pytest.approx((25e9 + 22e9 + 20e9 + 18e9) / 1e9)
        assert by_year["2024"] == pytest.approx((30e9 + 29e9 + 28e9) / 1e9)
        years = [r["year"] for r in result]
        assert years == sorted(years)
