"""
test_m2_zero_valid_completeness.py — Regression tests for Cycle 6 fix M-2.

Bug (pre-fix):
    Three locations treated numeric zero (0) as a missing/invalid value:
    1. fundamentals_service.py:554  — completeness score for DCF inputs
    2. validation_utils.py:38       — fields_present()
    3. validation_utils.py:52-54    — completeness_score()

    This incorrectly penalised companies with legitimately zero financial
    values, e.g. net_debt=0 (no debt), capex=0 (asset-light), depreciation=0.
    A company with zero net debt would score lower than one with missing data.

Fix:
    Remove 0 from the "absent/invalid" tuple in all three locations.
    Use `is not None` or `not in (None, "")` instead of `not in (None, 0)`.
    Zero remains a valid numeric value; only None and empty-string indicate absence.

Run with:
    pytest repo/services/tests/test_m2_zero_valid_completeness.py -v
"""

import sys
from pathlib import Path
import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from utils.validation_utils import fields_present, completeness_score


# ---------------------------------------------------------------------------
# fields_present()
# ---------------------------------------------------------------------------

class TestFieldsPresent:

    def test_zero_counts_as_present(self):
        """Zero is a valid numeric value — must NOT be treated as missing."""
        ok, missing = fields_present({"net_debt": 0}, ["net_debt"])
        assert ok is True, "net_debt=0 should be counted as present — M-2 fix not applied"
        assert missing == []

    def test_none_is_missing(self):
        ok, missing = fields_present({"net_debt": None}, ["net_debt"])
        assert ok is False
        assert "net_debt" in missing

    def test_empty_string_is_missing(self):
        ok, missing = fields_present({"name": ""}, ["name"])
        assert ok is False
        assert "name" in missing

    def test_negative_zero_counts_as_present(self):
        """Negative zero is still zero — also valid."""
        ok, missing = fields_present({"x": -0}, ["x"])
        assert ok is True

    def test_multiple_fields_zero_all_present(self):
        data = {"a": 0, "b": 0, "c": 100}
        ok, missing = fields_present(data, ["a", "b", "c"])
        assert ok is True
        assert missing == []

    def test_mixed_missing_and_zero(self):
        data = {"net_debt": 0, "capex": None, "revenue": 1e9}
        ok, missing = fields_present(data, ["net_debt", "capex", "revenue"])
        assert ok is False
        assert "capex" in missing
        assert "net_debt" not in missing


# ---------------------------------------------------------------------------
# completeness_score()
# ---------------------------------------------------------------------------

class TestCompletenessScore:

    def test_zero_counts_toward_completeness(self):
        """A single field with value 0 → completeness = 1.0 (fully complete)."""
        score = completeness_score({"net_debt": 0}, ["net_debt"])
        assert score == pytest.approx(1.0), (
            "net_debt=0 must count as present — M-2 fix not applied"
        )

    def test_none_does_not_count(self):
        score = completeness_score({"net_debt": None}, ["net_debt"])
        assert score == pytest.approx(0.0)

    def test_empty_string_does_not_count(self):
        score = completeness_score({"ticker": ""}, ["ticker"])
        assert score == pytest.approx(0.0)

    def test_all_zeros_full_score(self):
        """All-zero DCF inputs still represent a complete (if unusual) dataset."""
        data = {k: 0 for k in ["revenue_ttm", "ebit_margin", "net_debt", "capex"]}
        score = completeness_score(data, list(data.keys()))
        assert score == pytest.approx(1.0)

    def test_mix_of_zero_none_and_value(self):
        """2 of 4 fields present (0 and 100 count; None and [] do not)."""
        data = {"a": 0, "b": None, "c": 100, "d": []}
        score = completeness_score(data, ["a", "b", "c", "d"])
        assert score == pytest.approx(0.5)

    def test_empty_field_list_returns_one(self):
        assert completeness_score({}, []) == pytest.approx(1.0)

    def test_pre_fix_regression_zero_no_longer_penalised(self):
        """
        Pre-fix: {'net_debt': 0} scored 0.0 (treated as missing).
        Post-fix: must score 1.0.
        """
        pre_fix_would_give = 0.0
        actual = completeness_score({"net_debt": 0}, ["net_debt"])
        assert actual != pre_fix_would_give, (
            "net_debt=0 is still treated as missing — M-2 fix not applied"
        )
        assert actual == pytest.approx(1.0)
