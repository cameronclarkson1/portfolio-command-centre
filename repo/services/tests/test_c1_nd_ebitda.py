"""
test_c1_nd_ebitda.py — Regression tests for Cycle 5 fix C-1.

Bug (pre-fix):
    build_scoring_inputs() computed net_debt_to_ebitda using a single quarter's
    EBITDA (incomes[0]["ebitda"]) as the denominator.  Balance-sheet net debt is
    an annual / point-in-time figure, so dividing it by one quarter of EBITDA
    inflated the ratio by approximately 4×.  A company with correct ND/EBITDA=1.5
    would appear as 6.0, scoring 5/100 instead of 80/100 on the safety scale.

Fix:
    Sum EBITDA over all available quarterly records (up to 4) to form TTM EBITDA
    before dividing.

Tests cover:
  - Correct TTM EBITDA (4 quarters summed)
  - Pre-fix 4× inflation no longer present
  - Varying quarterly EBITDA values
  - Three quarters available (partial year)
  - Zero EBITDA (guard: ratio omitted)
  - Negative TTM EBITDA (guard: ratio omitted)
  - Missing (None) EBITDA fields
  - Empty statements (no data)
  - Net cash position (negative net debt)
  - Extreme leverage scenario
  - Safety score: low-leverage vs high-leverage comparison
  - Safety score: missing ND/EBITDA does not produce artificially favourable result

Run with:
    pytest repo/services/tests/test_c1_nd_ebitda.py -v
"""

import sys
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from services.scoring_service import build_scoring_inputs, score_safety


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stmts(income_quarters=None, balance_net_debt=None):
    """Build a minimal statements dict for scoring_service tests."""
    balance = [{"net_debt": balance_net_debt}] if balance_net_debt is not None else []
    return {
        "income":   income_quarters or [],
        "cashflow": [],
        "balance":  balance,
    }


def _result(income_quarters, balance_net_debt):
    """Call build_scoring_inputs with minimal stub args and return the dict."""
    stmts = _stmts(income_quarters, balance_net_debt)
    return build_scoring_inputs({}, {}, stmts, [], None, None)


# ---------------------------------------------------------------------------
# C-1 — ND/EBITDA calculation
# ---------------------------------------------------------------------------

class TestNdEbitdaCalculation:

    def test_four_quarters_ttm_ebitda(self):
        """Core fix: 4 quarters each EBITDA=500 → TTM=2000; net_debt=3000 → ratio=1.5."""
        r = _result([{"ebitda": 500}] * 4, balance_net_debt=3000)
        assert r["net_debt_to_ebitda"] == pytest.approx(1.5)

    def test_single_quarter_no_longer_used(self):
        """Pre-fix ratio would have been 3000/500=6.0.  Fix gives 3000/2000=1.5."""
        r = _result([{"ebitda": 500}] * 4, balance_net_debt=3000)
        assert r["net_debt_to_ebitda"] != pytest.approx(6.0), (
            "Still using single-quarter EBITDA — C-1 fix not applied"
        )
        assert r["net_debt_to_ebitda"] == pytest.approx(1.5)

    def test_varying_quarterly_ebitda(self):
        """Varying quarterly EBITDA: TTM is the actual sum, not the most-recent quarter."""
        # Quarters (most-recent first): 1000, 2000, 1500, 500 → TTM=5000
        r = _result(
            [{"ebitda": q} for q in [1000, 2000, 1500, 500]],
            balance_net_debt=10_000,
        )
        assert r["net_debt_to_ebitda"] == pytest.approx(2.0)  # 10000/5000

    def test_three_quarters_available(self):
        """Only 3 quarterly records: use the sum of those 3 quarters."""
        # 3 quarters × 500 = 1500 (no annualisation for ND/EBITDA)
        r = _result([{"ebitda": 500}] * 3, balance_net_debt=3000)
        assert r["net_debt_to_ebitda"] == pytest.approx(2.0)  # 3000/1500

    def test_zero_ebitda_returns_none(self):
        """Zero EBITDA: guard prevents division; ratio must be None."""
        r = _result([{"ebitda": 0}] * 4, balance_net_debt=1000)
        assert r["net_debt_to_ebitda"] is None

    def test_negative_ttm_ebitda_returns_none(self):
        """Negative TTM EBITDA: distressed company; ratio must be None (no divide by negative)."""
        r = _result([{"ebitda": -500}] * 4, balance_net_debt=1000)
        assert r["net_debt_to_ebitda"] is None

    def test_mixed_negative_ebitda_negative_sum(self):
        """Quarters with mixed sign that net to negative TTM: ratio must be None."""
        # Sum = -200 + 100 + 100 - 300 = -300 → guard fires
        r = _result(
            [{"ebitda": q} for q in [-200, 100, 100, -300]],
            balance_net_debt=1000,
        )
        assert r["net_debt_to_ebitda"] is None

    def test_missing_ebitda_fields_return_none(self):
        """All EBITDA fields are None: sum=0.0; ratio must be None."""
        r = _result([{"ebitda": None}] * 4, balance_net_debt=1000)
        assert r["net_debt_to_ebitda"] is None

    def test_missing_ebitda_key_in_quarter(self):
        """EBITDA key absent entirely from quarter dicts: sum=0.0; ratio must be None."""
        r = _result([{}] * 4, balance_net_debt=1000)
        assert r["net_debt_to_ebitda"] is None

    def test_empty_statements_returns_none(self):
        """No financial data at all: ratio must be None."""
        r = build_scoring_inputs({}, {}, {}, [], None, None)
        assert r["net_debt_to_ebitda"] is None

    def test_missing_balance_sheet_returns_none(self):
        """Income data present but no balance sheet: ratio must be None."""
        stmts = {"income": [{"ebitda": 500}] * 4, "cashflow": [], "balance": []}
        r = build_scoring_inputs({}, {}, stmts, [], None, None)
        assert r["net_debt_to_ebitda"] is None

    def test_net_cash_position_negative_ratio(self):
        """Negative net debt (net cash): ratio is negative, preserved for safety scorer."""
        r = _result([{"ebitda": 500}] * 4, balance_net_debt=-2000)
        # -2000 / 2000 = -1.0 (net cash position)
        assert r["net_debt_to_ebitda"] == pytest.approx(-1.0)

    def test_extreme_leverage(self):
        """ND/EBITDA=10 (highly distressed): computed correctly."""
        # 4 quarters × 100 = 400 TTM EBITDA; net_debt=4000
        r = _result([{"ebitda": 100}] * 4, balance_net_debt=4000)
        assert r["net_debt_to_ebitda"] == pytest.approx(10.0)

    def test_zero_net_debt_zero_ratio(self):
        """Zero net debt: ratio is 0.0 (no leverage)."""
        r = _result([{"ebitda": 500}] * 4, balance_net_debt=0)
        assert r["net_debt_to_ebitda"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# C-1 — Safety score impact
# ---------------------------------------------------------------------------

class TestNdEbitdaSafetyScore:
    """
    Verify that the corrected ND/EBITDA maps to sensible safety bands.

    score_safety() ND/EBITDA bands (from scoring_service.py):
        < 0.00  → 100  (net cash)
        < 1.00  →  92
        < 2.00  →  80
        < 3.00  →  60
        < 4.00  →  38
        < 6.00  →  18
        else    →   5
    """

    def _safety_with_nd(self, nd_ebitda):
        """Return safety score with only ND/EBITDA populated (others None)."""
        return score_safety({
            "net_debt_to_ebitda": nd_ebitda,
            "debt_equity":        None,
            "beta":               None,
            "week52_drawdown":    None,
            "free_cash_flow":     None,
        })

    def test_correct_ttm_gives_better_safety_than_bug_inflated(self):
        """
        Company with true ND/EBITDA=1.5 (safe):
          Pre-fix inflated to 6.0 → band score  5
          Post-fix correct   1.5 → band score 80
        Safety score with correct ratio must exceed safety with inflated ratio.
        """
        safety_correct = self._safety_with_nd(1.5)   # post-fix: band → 80
        safety_buggy   = self._safety_with_nd(6.0)   # pre-fix inflation: band → 5
        assert safety_correct > safety_buggy, (
            f"Expected corrected ratio (nd=1.5, safety={safety_correct:.1f}) to score "
            f"higher than inflated ratio (nd=6.0, safety={safety_buggy:.1f})"
        )

    def test_net_cash_scores_100_on_nd(self):
        """Negative ND/EBITDA (net cash): ND band score must be 100."""
        safety = self._safety_with_nd(-1.0)
        assert safety == pytest.approx(100.0)

    def test_low_leverage_scores_high(self):
        """ND/EBITDA=0.5 (< 1.0 threshold): ND band score = 92."""
        # Only nd_ebitda populated → weighted avg uses only that input
        safety = self._safety_with_nd(0.5)
        assert safety == pytest.approx(92.0)

    def test_moderate_leverage_scores_mid(self):
        """ND/EBITDA=1.5 (< 2.0 threshold): ND band score = 80."""
        safety = self._safety_with_nd(1.5)
        assert safety == pytest.approx(80.0)

    def test_high_leverage_scores_low(self):
        """ND/EBITDA=5.0 (< 6.0 threshold): ND band score = 18."""
        safety = self._safety_with_nd(5.0)
        assert safety == pytest.approx(18.0)

    def test_extreme_leverage_scores_floor(self):
        """ND/EBITDA=10+ (> 6.0, last band): ND band score = 5."""
        safety = self._safety_with_nd(10.0)
        assert safety == pytest.approx(5.0)

    def test_missing_nd_ebitda_does_not_inflate_score(self):
        """
        Missing ND/EBITDA data: score_safety() should return None when ALL inputs
        are None — no input should silently produce an artificially high score.
        """
        safety = self._safety_with_nd(None)
        assert safety is None, (
            "Missing ND/EBITDA with all other inputs also None should yield None, "
            "not an inflated safety score"
        )

    def test_low_vs_high_leverage_ordering(self):
        """Low-leverage company must score higher than high-leverage company."""
        s_low  = self._safety_with_nd(1.0)   # < 2.0 → 80
        s_high = self._safety_with_nd(4.5)   # < 6.0 → 18
        assert s_low > s_high
