"""
test_h1_scoring_ttm.py — Regression tests for Cycle 6 fix H-1.

Bug (pre-fix):
    The local _ttm() helper inside build_scoring_inputs() was a plain sum
    of up to 4 quarters with no annualisation.  For companies with < 4 quarters
    of history (IPOs, partial years), free_cash_flow and net_income were
    understated by up to 4×, reducing quality and safety scores.

Fix:
    Added annualisation to _ttm(): when fewer than n (4) quarters are present,
    the sum is multiplied by n / n_actual, mirroring the shared ttm_sum() in
    utils/financial_calcs.py.  Returns None when no valid data is found.

Run with:
    pytest repo/services/tests/test_h1_scoring_ttm.py -v
"""

import sys
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from services.scoring_service import build_scoring_inputs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stmts(income=None, cashflow=None):
    return {
        "income":   income   or [],
        "cashflow": cashflow or [],
        "balance":  [],
    }


def _build(income=None, cashflow=None):
    return build_scoring_inputs({}, {}, _stmts(income, cashflow), [], None, None)


# ---------------------------------------------------------------------------
# free_cash_flow annualisation
# ---------------------------------------------------------------------------

class TestFreeCashFlowAnnualisation:

    def test_four_quarters_no_annualisation(self):
        """4 × 500 = 2000 — no scaling needed."""
        d = _build(cashflow=[{"free_cash_flow": 500}] * 4)
        assert d["free_cash_flow"] == pytest.approx(2000.0)

    def test_three_quarters_annualised(self):
        """3 × 500 = 1500 raw; annualised = 1500 × (4/3) = 2000."""
        d = _build(cashflow=[{"free_cash_flow": 500}] * 3)
        assert d["free_cash_flow"] == pytest.approx(2000.0)

    def test_two_quarters_annualised(self):
        """2 × 500 = 1000 raw; annualised = 1000 × (4/2) = 2000."""
        d = _build(cashflow=[{"free_cash_flow": 500}] * 2)
        assert d["free_cash_flow"] == pytest.approx(2000.0)

    def test_one_quarter_annualised(self):
        """1 × 500 = 500 raw; annualised = 500 × (4/1) = 2000."""
        d = _build(cashflow=[{"free_cash_flow": 500}] * 1)
        assert d["free_cash_flow"] == pytest.approx(2000.0)

    def test_no_data_returns_none(self):
        """No cashflow records → None."""
        d = _build(cashflow=[])
        assert d["free_cash_flow"] is None

    def test_all_none_fcf_returns_none(self):
        """All None values → found=False → None."""
        d = _build(cashflow=[{"free_cash_flow": None}] * 4)
        assert d["free_cash_flow"] is None

    def test_missing_field_returns_none(self):
        """Quarters without free_cash_flow key → None."""
        d = _build(cashflow=[{}] * 4)
        assert d["free_cash_flow"] is None

    def test_negative_fcf_annualised(self):
        """Negative FCF is a valid value and must be annualised too."""
        d = _build(cashflow=[{"free_cash_flow": -300}] * 2)
        assert d["free_cash_flow"] == pytest.approx(-1200.0)


# ---------------------------------------------------------------------------
# net_income annualisation (multi-field: "net_income" and "netIncome")
# ---------------------------------------------------------------------------

class TestNetIncomeAnnualisation:

    def test_four_quarters_net_income(self):
        d = _build(income=[{"net_income": 400}] * 4)
        assert d["net_income"] == pytest.approx(1600.0)

    def test_two_quarters_net_income_annualised(self):
        d = _build(income=[{"net_income": 400}] * 2)
        assert d["net_income"] == pytest.approx(1600.0)

    def test_one_quarter_net_income_annualised(self):
        d = _build(income=[{"net_income": 400}] * 1)
        assert d["net_income"] == pytest.approx(1600.0)

    def test_camel_case_net_income_field(self):
        """'netIncome' (camelCase) is an accepted fallback field name."""
        d = _build(income=[{"netIncome": 400}] * 2)
        assert d["net_income"] == pytest.approx(1600.0)

    def test_snake_case_preferred_over_camel(self):
        """When both are present, net_income takes precedence."""
        d = _build(income=[{"net_income": 400, "netIncome": 999}] * 4)
        assert d["net_income"] == pytest.approx(1600.0)

    def test_no_income_returns_none(self):
        d = _build(income=[])
        assert d["net_income"] is None

    def test_three_quarters_net_income_annualised(self):
        d = _build(income=[{"net_income": 300}] * 3)
        assert d["net_income"] == pytest.approx(1200.0)


# ---------------------------------------------------------------------------
# Pre-fix regression: 1 quarter no longer understates 4× relative to full year
# ---------------------------------------------------------------------------

class TestPreFixRegression:

    def test_single_quarter_matches_four_quarter_equivalent(self):
        """
        Pre-fix: 1 quarter FCF=500 → d["free_cash_flow"]=500 (4× understated).
        Post-fix: 1 quarter FCF=500 → d["free_cash_flow"]=2000 (annualised).
        """
        d_one  = _build(cashflow=[{"free_cash_flow": 500}] * 1)
        d_four = _build(cashflow=[{"free_cash_flow": 500}] * 4)
        assert d_one["free_cash_flow"] == pytest.approx(d_four["free_cash_flow"])
