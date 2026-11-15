"""
test_h4_fcf_cagr.py — Regression tests for Cycle 6 fix H-4 (corrected).

Original bug:
    FCF CAGR compared cashflows[0] (most-recent quarter) to cashflows[3]
    (3 quarters ago) using a ** (1/3) exponent — a 3-quarter window treated
    as a 3-year CAGR.

First fix attempt (incorrect):
    Used cashflows[0:4] vs cashflows[8:12] with ** (1/3).  But cashflows[8:12]
    ends at T-24mo (2 years ago), not 3 years ago.  The exponent 1/3 was
    mathematically wrong for a 2-year elapsed time.

Correct fix:
    - cashflows[0:4]   = TTM now, ending at T.
    - cashflows[12:16] = TTM ending at T-12 quarters = T-3 years.
    - Elapsed time between window ends = exactly 3 years → exponent 1/3 is correct.
    - Require >= 16 quarters (4 years of history).
    - Both TTM values must be positive.

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
# History requirement — 16 quarters minimum
# ---------------------------------------------------------------------------

class TestHistoryRequirement:

    def test_fewer_than_16_quarters_returns_none(self):
        """Correct fix requires 16 quarters; 15 must return None."""
        stmts = _stmts(_flat_quarters(1_000, 15))
        assert _cagr(stmts) is None

    def test_exactly_12_quarters_returns_none(self):
        """Prior (incorrect) fix fired at 12 quarters; correct fix must not."""
        stmts = _stmts(_flat_quarters(1_000, 12))
        assert _cagr(stmts) is None, (
            "12 quarters is only 2 years of old-window data — must return None"
        )

    def test_exactly_4_quarters_returns_none(self):
        """Original bug would compute with 4 quarters — post-fix must not."""
        stmts = _stmts(_flat_quarters(1_000, 4))
        assert _cagr(stmts) is None

    def test_exactly_16_quarters_computes(self):
        """16 quarters is the minimum for a valid 3-year TTM-to-TTM CAGR."""
        stmts = _stmts(_flat_quarters(1_000, 16))
        result = _cagr(stmts)
        assert result is not None
        assert result == pytest.approx(0.0)  # flat FCF → 0% CAGR

    def test_more_than_16_quarters_computes(self):
        """Extra history beyond 16 quarters — still valid."""
        stmts = _stmts(_flat_quarters(1_000, 20))
        assert _cagr(stmts) is not None


# ---------------------------------------------------------------------------
# Correct window: cashflows[0:4] vs cashflows[12:16]
# ---------------------------------------------------------------------------

class TestCorrectWindow:

    def test_flat_fcf_gives_zero_cagr(self):
        """All 16 quarters equal → TTM now = TTM old → CAGR = 0%."""
        stmts = _stmts(_flat_quarters(500, 16))
        assert _cagr(stmts) == pytest.approx(0.0)

    def test_fcf_doubling_over_3_years_gives_26_pct_cagr(self):
        """
        TTM old (q12–q15) = 4 × 500 = 2000.
        TTM now (q0–q3)   = 4 × 1000 = 4000.
        True 3-year CAGR  = (4000/2000)^(1/3) - 1 = 2^(1/3) - 1 ≈ 0.2599 (26.0%).
        """
        quarters = (
            [_quarter(1_000)] * 4   # q0–q3:   TTM now
            + [_quarter(750)]  * 4  # q4–q7:   middle (ignored)
            + [_quarter(600)]  * 4  # q8–q11:  middle (ignored)
            + [_quarter(500)]  * 4  # q12–q15: TTM old (3 years ago)
        )
        stmts = _stmts(quarters)
        result = _cagr(stmts)
        assert result is not None
        expected = 2 ** (1 / 3) - 1  # ≈ 0.2599
        assert result == pytest.approx(expected, rel=1e-4)

    def test_middle_8_quarters_do_not_affect_cagr(self):
        """
        Quarters 4–11 are not part of either TTM window and must have no
        effect on the CAGR result.  Setting them to extreme values verifies
        they are not accidentally included.
        """
        base_quarters = (
            [_quarter(1_000)] * 4   # q0–q3:   TTM now
            + [_quarter(500)]  * 4  # q12–q15: TTM old
        )
        # Normal middle quarters
        normal = _cagr(_stmts(base_quarters[:4] + [_quarter(750)] * 8 + base_quarters[4:]))
        # Extreme middle quarters (should give same result)
        extreme = _cagr(_stmts(base_quarters[:4] + [_quarter(99_999)] * 8 + base_quarters[4:]))
        assert normal == pytest.approx(extreme, rel=1e-6)

    def test_prior_incorrect_12q_window_no_longer_used(self):
        """
        Old (incorrect) fix compared TTM now vs cashflows[8:12], which is only
        2 years apart.  Confirm we now require 16 quarters and use [12:16].
        12 quarters of data must return None.
        """
        quarters_12 = [_quarter(1_000)] * 4 + [_quarter(500)] * 8
        stmts = _stmts(quarters_12)
        assert _cagr(stmts) is None, (
            "cashflows[8:12] window (2-year gap) must no longer fire"
        )

    def test_uses_cashflows_0_to_4_as_ttm_now(self):
        """
        TTM now must sum cashflows[0:4], not just cashflows[0].
        q0=400, q1=300, q2=200, q3=100 → TTM now = 1000.
        TTM old (q12–q15) = 4 × 200 = 800.
        CAGR = (1000/800)^(1/3) - 1.
        """
        quarters = (
            [_quarter(400), _quarter(300), _quarter(200), _quarter(100)]  # q0–q3
            + [_quarter(200)] * 8                                          # q4–q11
            + [_quarter(200)] * 4                                          # q12–q15
        )
        stmts = _stmts(quarters)
        result = _cagr(stmts)
        assert result is not None
        expected = (1000 / 800) ** (1 / 3) - 1
        assert result == pytest.approx(expected, rel=1e-4)

    def test_uses_cashflows_12_to_16_as_ttm_old(self):
        """
        TTM old must sum cashflows[12:16], not any earlier or later window.
        q0–q3 = 4 × 1000 = 4000; q12=100, q13=200, q14=300, q15=400 → TTM old = 1000.
        CAGR = (4000/1000)^(1/3) - 1.
        """
        quarters = (
            [_quarter(1_000)] * 4                                           # q0–q3
            + [_quarter(500)] * 8                                           # q4–q11
            + [_quarter(100), _quarter(200), _quarter(300), _quarter(400)]  # q12–q15
        )
        stmts = _stmts(quarters)
        result = _cagr(stmts)
        assert result is not None
        expected = (4000 / 1000) ** (1 / 3) - 1
        assert result == pytest.approx(expected, rel=1e-4)

    def test_exponent_is_one_third(self):
        """
        Verify the exponent is 1/3, not 1/2.  With FCF tripling in 3 years,
        CAGR should be 3^(1/3)-1 ≈ 44.2%, not 3^(1/2)-1 ≈ 73.2%.
        """
        quarters = (
            [_quarter(3_000)] * 4   # TTM now = 12_000
            + [_quarter(1_000)] * 12  # TTM old (q12–q15) = 4_000
        )
        stmts = _stmts(quarters)
        result = _cagr(stmts)
        assert result is not None
        # 3-year CAGR with 1/3 exponent: (12000/4000)^(1/3) - 1 = 3^(1/3) - 1
        expected_one_third = 3 ** (1 / 3) - 1  # ≈ 0.4422
        wrong_one_half     = 3 ** (1 / 2) - 1  # ≈ 0.7321
        assert result == pytest.approx(expected_one_third, rel=1e-4)
        assert result != pytest.approx(wrong_one_half, rel=1e-2)


# ---------------------------------------------------------------------------
# Negative and zero FCF guards
# ---------------------------------------------------------------------------

class TestNegativeAndZeroGuards:

    def test_negative_current_ttm_returns_none(self):
        """Negative current TTM FCF must return None — not nan."""
        quarters = [_quarter(-100)] * 4 + [_quarter(100)] * 12
        stmts = _stmts(quarters)
        result = _cagr(stmts)
        assert result is None

    def test_negative_old_ttm_returns_none(self):
        """Negative TTM 3 years ago — no meaningful CAGR possible."""
        quarters = [_quarter(100)] * 12 + [_quarter(-100)] * 4
        stmts = _stmts(quarters)
        assert _cagr(stmts) is None

    def test_zero_current_ttm_returns_none(self):
        """Zero TTM FCF now → not > 0 guard fires → None."""
        quarters = [_quarter(0)] * 4 + [_quarter(100)] * 12
        stmts = _stmts(quarters)
        assert _cagr(stmts) is None

    def test_zero_old_ttm_returns_none(self):
        """Zero TTM 3 years ago — division would be meaningless."""
        quarters = [_quarter(100)] * 12 + [_quarter(0)] * 4
        stmts = _stmts(quarters)
        assert _cagr(stmts) is None

    def test_missing_fcf_field_returns_none(self):
        """Quarters without free_cash_flow field → ttm_sum returns 0 → None."""
        stmts = _stmts([{}] * 16)
        assert _cagr(stmts) is None

    def test_none_fcf_values_return_none(self):
        """All None FCF values → ttm_sum returns 0 → None."""
        stmts = _stmts([_quarter(None)] * 16)
        assert _cagr(stmts) is None

    def test_no_nan_propagation(self):
        """Under no valid input scenario should fcf_cagr be nan."""
        for quarters in [
            [_quarter(-1)] * 16,
            [_quarter(0)] * 16,
            [_quarter(None)] * 16,
            [{}] * 16,
        ]:
            result = _cagr(_stmts(quarters))
            assert result is None or not math.isnan(result), (
                f"fcf_cagr is nan for input: {quarters[0]}"
            )
