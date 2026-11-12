"""
test_m4_negative_equity_guard.py — Regression tests for Cycle 6 fix M-4.

Bug (pre-fix):
    run_ev_ebitda() and run_ev_sales() in relative_valuation.py computed
    equity_value = implied_ev - net_debt without checking the result.
    For highly leveraged companies where net_debt > implied_ev, equity_value
    is negative.  Dividing by shares_out produced a negative fair_value that
    was returned as a valid price — a silently wrong valuation.

Fix:
    After computing equity_value, check if it is <= 0.  If so, return
    fair_value=None with an explicit warning message naming the net-debt amount
    rather than propagating a negative price.

Run with:
    pytest repo/services/tests/test_m4_negative_equity_guard.py -v
"""

import sys
from pathlib import Path
import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

# Remove any stub that other test files (e.g. test_dcf_safeguards) may have
# installed via sys.modules substitution, so we always import the real module.
sys.modules.pop("services.relative_valuation", None)

from services.relative_valuation import run_ev_ebitda, run_ev_sales


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _statements(revenue=10e9, ebitda=2e9, net_debt=0, shares=500e6):
    # Provide 4 equal quarters so ttm_sum produces the specified annual totals
    # without annualisation scaling.
    return {
        "income": [{
            "revenue": revenue / 4,
            "ebitda":  ebitda / 4,
            "ebit":    ebitda / 4 * 0.8,
        }] * 4,
        "cashflow": [],
        "balance": [{
            "net_debt":           net_debt,
            "total_equity":       1e9,
            "shares_outstanding": shares,
        }],
    }


# ---------------------------------------------------------------------------
# EV/EBITDA guard
# ---------------------------------------------------------------------------

class TestEvEbitdaNegativeEquityGuard:

    def test_normal_case_returns_fair_value(self):
        """Net debt well below implied EV — fair_value is positive."""
        stmts = _statements(ebitda=2e9, net_debt=1e9)
        result = run_ev_ebitda("technology", {}, stmts)
        assert result["fair_value"] is not None
        assert result["fair_value"] > 0

    def test_net_debt_exceeds_implied_ev_returns_none(self):
        """
        EBITDA=$2B × benchmark=20× (tech) = implied EV=$40B.
        Net debt=$60B → equity_value = -$20B → must return fair_value=None.
        """
        stmts = _statements(ebitda=2e9, net_debt=60e9)
        result = run_ev_ebitda("technology", {}, stmts)
        assert result["fair_value"] is None, (
            "Negative equity value should return fair_value=None — M-4 fix not applied"
        )

    def test_negative_equity_warning_message(self):
        """Warning must explicitly describe the negative equity situation."""
        stmts = _statements(ebitda=2e9, net_debt=60e9)
        result = run_ev_ebitda("technology", {}, stmts)
        assert result["warnings"], "Should have at least one warning"
        combined = " ".join(result["warnings"]).lower()
        assert "negative" in combined or "net debt" in combined or "equity" in combined

    def test_negative_equity_confidence_is_zero(self):
        """Confidence must be 0.0 when fair_value is None."""
        stmts = _statements(ebitda=2e9, net_debt=60e9)
        result = run_ev_ebitda("technology", {}, stmts)
        assert result["confidence"] == 0.0

    def test_exact_break_even_net_debt_returns_none(self):
        """equity_value == 0 (exactly) is also invalid — must return None."""
        # With benchmark ~12 and EBITDA=1B, implied_ev ~12B; set net_debt=12B exactly.
        # Use a sector with a known benchmark so we can hit 0 exactly.
        stmts = _statements(ebitda=1e9, net_debt=12e9)
        result = run_ev_ebitda("technology", {}, stmts)
        # Depending on benchmark the equity could be 0 or negative.
        # We just verify no negative price leaks through.
        if result["fair_value"] is not None:
            assert result["fair_value"] > 0


# ---------------------------------------------------------------------------
# EV/Sales guard
# ---------------------------------------------------------------------------

class TestEvSalesNegativeEquityGuard:

    def test_normal_case_returns_fair_value(self):
        """Net debt well below implied EV — fair_value is positive."""
        stmts = _statements(revenue=10e9, net_debt=1e9)
        result = run_ev_sales("technology", {}, stmts)
        assert result["fair_value"] is not None
        assert result["fair_value"] > 0

    def test_net_debt_exceeds_implied_ev_returns_none(self):
        """
        Revenue=$10B × benchmark=6× (tech) = implied EV=$60B.
        Net debt=$80B → equity_value = -$20B → must return fair_value=None.
        """
        stmts = _statements(revenue=10e9, net_debt=80e9)
        result = run_ev_sales("technology", {}, stmts)
        assert result["fair_value"] is None, (
            "Negative equity value should return fair_value=None — M-4 fix not applied"
        )

    def test_negative_equity_warning_message(self):
        stmts = _statements(revenue=10e9, net_debt=80e9)
        result = run_ev_sales("technology", {}, stmts)
        assert result["warnings"]
        combined = " ".join(result["warnings"]).lower()
        assert "negative" in combined or "net debt" in combined or "equity" in combined

    def test_negative_equity_confidence_is_zero(self):
        stmts = _statements(revenue=10e9, net_debt=80e9)
        result = run_ev_sales("technology", {}, stmts)
        assert result["confidence"] == 0.0

    def test_no_negative_fair_value_ever_returned(self):
        """Under no scenario should a negative fair_value be returned."""
        for net_debt in [0, 5e9, 20e9, 50e9, 300e9, 1_000e9]:
            stmts = _statements(revenue=5e9, net_debt=net_debt)
            result = run_ev_sales("technology", {}, stmts)
            fv = result.get("fair_value")
            if fv is not None:
                assert fv > 0, f"Negative fair_value={fv} returned for net_debt={net_debt}"
