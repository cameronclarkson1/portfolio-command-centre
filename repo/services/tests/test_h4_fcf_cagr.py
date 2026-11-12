"""
test_h4_fcf_cagr.py — Regression tests for Cycle 6 fix H-4.

Bug (pre-fix):
    FCF CAGR compared cashflows[0] (most-recent quarter) to cashflows[3]
    (3 quarters ago) using a ** (1/3) exponent — a 3-quarter window treated
    as a 3-year CAGR.  Negative current FCF produced nan via fractional
    exponent of a negative base.  The minimum history guard was 4 quarters
    (1 year) instead of 12 (3 years).

Fix:
    - Require >= 12 quarters of cashflow history.
    - Compare TTM now (cashflows[:4]) vs TTM 3 years ago (cashflows[8:12]).
    - Both TTM values must be positive before computing the CAGR.
    - ttm_sum() used for both windows (consistent annualisation if partial).

Run with:
    pytest repo/services/tests/test_h4_fcf_cagr.py -v
"""

import sys
import math
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from services.scoring_service import build_scoring_inputs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quarter(fcf: float | None) -> dict:
    return {"free_cash_flow": fcf}


def _stmts(cashflow_quarters: list) -> dict:
    return {"income": [], "cashflow": cashflow_quarters, "balance": []}


def _cagr(stmts):
    r = build_scoring_inputs({}, {}, stmts, [], None, None)
    return r["fcf_cagr"]


def _flat_quarters(value: float, n: int) -> list:
    return [_quarter(value)] * n


# ---------------------------------------------------------------------------
# History requirement
# ---------------------------------------------------------------------------

class TestHistoryRequirement:

    def test_fewer_than_12_quarters_returns_none(self):
        """Pre-fix fired with 4 quarters; fix requires 12."""
        stmts = _stmts(_flat_quarters(1_000, 11))
        assert _cagr(stmts) is None

    def test_exactly_4_quarters_returns_none(self):
        """Original bug would compute with 4 quarters — post-fix must not."""
        stmts = _stmts(_flat_quarters(1_000, 4))
        assert _cagr(stmts) is None

    def test_exactly_12_quarters_computes(self):
        """12 quarters is the minimum for a valid 3-year CAGR."""
        stmts = _stmts(_flat_quarters(1_000, 12))
        result = _cagr(stmts)
        assert result is not None
        assert result == pytest.approx(0.0)  # flat FCF → 0% CAGR

    def test_more_than_12_quarters_computes(self):
        """Extra history beyond 12 quarters — still valid."""
        stmts = _stmts(_flat_quarters(1_000, 16))
        assert _cagr(stmts) is not None


# ---------------------------------------------------------------------------
# Correct window: TTM now vs TTM 3 years ago
# ---------------------------------------------------------------------------

class TestCorrectWindow:

    def test_flat_fcf_gives_zero_cagr(self):
        """All 12 quarters equal → TTM now = TTM old → CAGR = 0%."""
        stmts = _stmts(_flat_quarters(500, 12))
        assert _cagr(stmts) == pytest.approx(0.0)

    def test_doubling_fcf_gives_26_pct_cagr(self):
        """
        TTM old = 4 × 500 = 2000; TTM now = 4 × 1000 = 4000.
        CAGR = (4000/2000)^(1/3) - 1 = 2^(1/3) - 1 ≈ 0.2599.
        """
        # Most recent 4 quarters: 1000; oldest 4 quarters: 500; 4 middle: 750
        quarters = [_quarter(1_000)] * 4 + [_quarter(750)] * 4 + [_quarter(500)] * 4
        stmts = _stmts(quarters)
        result = _cagr(stmts)
        assert result is not None
        assert result == pytest.approx(2 ** (1 / 3) - 1, rel=1e-4)

    def test_pre_fix_window_no_longer_used(self):
        """
        Pre-fix compared cashflows[0] vs cashflows[3] (3 quarters apart).
        With FCF growing from 500 (old) to 1000 (new) over 3 quarters,
        pre-fix gave (1000/500)^(1/3) - 1 ≈ 0.26.
        Post-fix compares TTM to TTM and correctly requires 12 quarters.
        """
        # Only 4 quarters → returns None, not the erroneous 26% figure.
        quarters_4 = [_quarter(1_000), _quarter(900), _quarter(700), _quarter(500)]
        stmts = _stmts(quarters_4)
        assert _cagr(stmts) is None, "Pre-fix window (4 quarters) should no longer fire"


# ---------------------------------------------------------------------------
# Negative and zero FCF guards
# ---------------------------------------------------------------------------

class TestNegativeAndZeroGuards:

    def test_negative_current_ttm_returns_none(self):
        """Negative current TTM FCF must return None — not nan."""
        quarters = [_quarter(-100)] * 4 + [_quarter(100)] * 8
        stmts = _stmts(quarters)
        result = _cagr(stmts)
        assert result is None
        # Explicitly ensure no nan leaked through
        if result is not None:
            assert not math.isnan(result)

    def test_negative_old_ttm_returns_none(self):
        """Negative TTM 3 years ago — no meaningful CAGR possible."""
        quarters = [_quarter(100)] * 4 + [_quarter(100)] * 4 + [_quarter(-100)] * 4
        stmts = _stmts(quarters)
        assert _cagr(stmts) is None

    def test_zero_current_ttm_returns_none(self):
        """Zero TTM FCF now → not > 0 guard fires → None."""
        quarters = [_quarter(0)] * 4 + [_quarter(100)] * 8
        stmts = _stmts(quarters)
        assert _cagr(stmts) is None

    def test_zero_old_ttm_returns_none(self):
        """Zero TTM 3 years ago — division would be meaningless."""
        quarters = [_quarter(100)] * 8 + [_quarter(0)] * 4
        stmts = _stmts(quarters)
        assert _cagr(stmts) is None

    def test_missing_fcf_field_returns_none(self):
        """Quarters without free_cash_flow field → ttm_sum returns 0 → None."""
        stmts = _stmts([{}] * 12)
        assert _cagr(stmts) is None

    def test_none_fcf_values_return_none(self):
        """All None FCF values → ttm_sum returns 0 → None."""
        stmts = _stmts([_quarter(None)] * 12)
        assert _cagr(stmts) is None

    def test_no_nan_propagation(self):
        """Under no valid input scenario should fcf_cagr be nan."""
        import math
        for quarters in [
            [_quarter(-1)] * 12,
            [_quarter(0)] * 12,
            [_quarter(None)] * 12,
            [{}] * 12,
        ]:
            result = _cagr(_stmts(quarters))
            assert result is None or not math.isnan(result), (
                f"fcf_cagr is nan for input: {quarters[0]}"
            )


# ---------------------------------------------------------------------------
# TTM window accuracy
# ---------------------------------------------------------------------------

class TestTtmWindowAccuracy:

    def test_uses_first_4_quarters_as_ttm_now(self):
        """
        CAGR must use the sum of cashflows[:4] (TTM now), not cashflows[0] alone.
        If only cashflows[0] were used, TTM now = 400.
        If cashflows[:4] are used, TTM now = 400 + 300 + 200 + 100 = 1000.
        """
        # TTM now: 400+300+200+100=1000; TTM old (q8-11): 4×200=800
        quarters = (
            [_quarter(400), _quarter(300), _quarter(200), _quarter(100)]  # now
            + [_quarter(200)] * 4                                          # middle
            + [_quarter(200)] * 4                                          # old
        )
        stmts = _stmts(quarters)
        result = _cagr(stmts)
        assert result is not None
        expected = (1000 / 800) ** (1 / 3) - 1
        assert result == pytest.approx(expected, rel=1e-4)

    def test_uses_cashflows_8_to_12_as_ttm_old(self):
        """
        TTM old must come from cashflows[8:12], not cashflows[3] alone.
        """
        # TTM now: 4×1000=4000; TTM old: 100+200+300+400=1000
        quarters = (
            [_quarter(1_000)] * 4                                           # now
            + [_quarter(500)] * 4                                           # middle
            + [_quarter(100), _quarter(200), _quarter(300), _quarter(400)]  # old
        )
        stmts = _stmts(quarters)
        result = _cagr(stmts)
        assert result is not None
        expected = (4000 / 1000) ** (1 / 3) - 1
        assert result == pytest.approx(expected, rel=1e-4)
