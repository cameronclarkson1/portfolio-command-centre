"""
test_ttm_services.py — Annualisation tests for reit_valuation and relative_valuation.

Verifies that _annualise, _ttm_income, and _ttm_cashflow correctly annualise
TTM figures when fewer than 4 quarters of data are available, using the shared
ttm_sum implementation from utils.financial_calcs.

Also verifies end-to-end: run_pffo and run_pe produce higher fair values when
annualisation is applied to 3-quarter data than when it is not.

No live network calls — reit_valuation stubs logging; relative_valuation has
no external imports.
Run with: pytest repo/services/tests/test_ttm_services.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path + stubs
# ---------------------------------------------------------------------------

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

_logger_inst = MagicMock()


def _stub(name, **attrs):
    m = MagicMock()
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


_stub(
    "utils.logging_utils",
    get_logger=lambda _: _logger_inst,
    log_cache_hit=MagicMock(),
    log_cache_miss=MagicMock(),
    log_fallback=MagicMock(),
)

# Remove any stubs placed by earlier test files so we load the real modules
sys.modules.pop("services.reit_valuation", None)
sys.modules.pop("services.relative_valuation", None)
sys.modules.pop("utils.financial_calcs", None)

from services.reit_valuation import _annualise, run_pffo, run_paffo  # noqa: E402
from services.relative_valuation import _ttm_income, _ttm_cashflow, run_pe, run_ev_ebitda  # noqa: E402


# ---------------------------------------------------------------------------
# _annualise — reit_valuation helper
# ---------------------------------------------------------------------------

def _stmts(income=None, cashflow=None, balance=None):
    return {
        "income":   income   or [],
        "cashflow": cashflow or [],
        "balance":  balance  or [],
    }


class TestAnnualise:
    def test_four_quarters_no_annualisation(self):
        quarters = [{"net_income": 100}, {"net_income": 100},
                    {"net_income": 100}, {"net_income": 100}]
        stmts = _stmts(income=quarters)
        assert _annualise(stmts, "net_income", "income") == pytest.approx(400.0)

    def test_three_quarters_annualised(self):
        quarters = [{"net_income": 100}, {"net_income": 100}, {"net_income": 100}]
        stmts = _stmts(income=quarters)
        # 300 × (4/3) = 400.0
        assert _annualise(stmts, "net_income", "income") == pytest.approx(400.0)

    def test_two_quarters_annualised(self):
        quarters = [{"net_income": 100}, {"net_income": 100}]
        stmts = _stmts(income=quarters)
        # 200 × 2 = 400.0
        assert _annualise(stmts, "net_income", "income") == pytest.approx(400.0)

    def test_one_quarter_annualised(self):
        quarters = [{"net_income": 100}]
        stmts = _stmts(income=quarters)
        # 100 × 4 = 400.0
        assert _annualise(stmts, "net_income", "income") == pytest.approx(400.0)

    def test_empty_list_returns_none(self):
        stmts = _stmts(income=[])
        assert _annualise(stmts, "net_income", "income") is None

    def test_all_zero_returns_none(self):
        quarters = [{"net_income": 0}, {"net_income": 0}]
        stmts = _stmts(income=quarters)
        assert _annualise(stmts, "net_income", "income") is None

    def test_missing_statement_type_returns_none(self):
        stmts = {}
        assert _annualise(stmts, "net_income", "income") is None

    def test_cashflow_field_annualised(self):
        quarters = [{"depreciation": 50}, {"depreciation": 50}]
        stmts = _stmts(cashflow=quarters)
        # 100 × 2 = 200.0
        assert _annualise(stmts, "depreciation", "cashflow") == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# _ttm_income — relative_valuation helper
# ---------------------------------------------------------------------------

class TestTtmIncome:
    def test_four_quarters_no_annualisation(self):
        income = [{"revenue": 100, "net_income": 10}] * 4
        result = _ttm_income({"income": income})
        assert result["revenue"] == pytest.approx(400.0)
        assert result["net_income"] == pytest.approx(40.0)

    def test_three_quarters_annualised(self):
        income = [{"revenue": 100, "ebitda": 30}] * 3
        result = _ttm_income({"income": income})
        # 300 × (4/3) = 400
        assert result["revenue"] == pytest.approx(400.0)
        # 90 × (4/3) = 120
        assert result["ebitda"] == pytest.approx(120.0)

    def test_two_quarters_annualised(self):
        income = [{"revenue": 100}] * 2
        result = _ttm_income({"income": income})
        # 200 × 2 = 400
        assert result["revenue"] == pytest.approx(400.0)

    def test_one_quarter_annualised(self):
        income = [{"revenue": 100}]
        result = _ttm_income({"income": income})
        # 100 × 4 = 400
        assert result["revenue"] == pytest.approx(400.0)

    def test_missing_field_returns_none(self):
        # Field not present in any quarter → ttm_sum returns 0 → or None → None
        income = [{"revenue": 100}] * 3
        result = _ttm_income({"income": income})
        assert result["eps"] is None

    def test_empty_income_returns_all_none(self):
        result = _ttm_income({"income": []})
        for field in ("revenue", "net_income", "ebitda", "eps"):
            assert result[field] is None


# ---------------------------------------------------------------------------
# _ttm_cashflow — relative_valuation helper
# ---------------------------------------------------------------------------

class TestTtmCashflow:
    def test_three_quarters_annualised(self):
        cashflow = [{"operating_cash_flow": 60}] * 3
        result = _ttm_cashflow({"cashflow": cashflow})
        # 180 × (4/3) = 240
        assert result["operating_cash_flow"] == pytest.approx(240.0)

    def test_negative_capex_annualised(self):
        cashflow = [{"capex": -50}] * 2
        result = _ttm_cashflow({"cashflow": cashflow})
        # -100 × 2 = -200
        assert result["capex"] == pytest.approx(-200.0)

    def test_empty_cashflow_returns_all_none(self):
        result = _ttm_cashflow({"cashflow": []})
        for field in ("operating_cash_flow", "capex", "free_cash_flow"):
            assert result[field] is None


# ---------------------------------------------------------------------------
# End-to-end: run_pffo produces annualised result with 3 quarters
# ---------------------------------------------------------------------------

class TestRunPffoAnnualisation:
    def _make_stmts(self, n_quarters: int) -> dict:
        quarters = [{"net_income": 250_000_000, "depreciation": 50_000_000}] * n_quarters
        return {
            "income":   quarters,
            "cashflow": quarters,
            "balance":  [{"shares_outstanding": 1_000_000_000}],
        }

    def test_four_quarters_baseline(self):
        stmts = self._make_stmts(4)
        result = run_pffo({}, stmts, ticker="TEST")
        assert result["fair_value"] is not None
        # net_income=1B, dep=200M, ffo=1.2B, ffo/share=1.20, fv=1.20*18=21.60
        assert result["inputs_used"]["ffo_ttm"] == pytest.approx(1_200_000_000.0)

    def test_three_quarters_gives_annualised_ffo(self):
        stmts = self._make_stmts(3)
        result = run_pffo({}, stmts, ticker="TEST")
        assert result["fair_value"] is not None
        # net_income annualised: 3×250M × 4/3 = 1B; dep: 3×50M × 4/3 = 200M
        # ffo_ttm = 1.2B (same as 4-quarter baseline)
        assert result["inputs_used"]["ffo_ttm"] == pytest.approx(1_200_000_000.0)

    def test_two_quarters_gives_annualised_ffo(self):
        stmts = self._make_stmts(2)
        result = run_pffo({}, stmts, ticker="TEST")
        assert result["fair_value"] is not None
        # net_income: 2×250M × 2 = 1B; dep: 2×50M × 2 = 200M
        assert result["inputs_used"]["ffo_ttm"] == pytest.approx(1_200_000_000.0)


# ---------------------------------------------------------------------------
# End-to-end: run_pe produces annualised result with 3 quarters
# ---------------------------------------------------------------------------

class TestRunPeAnnualisation:
    def _make_stmts(self, n_quarters: int) -> dict:
        quarters = [{"eps": 2.0}] * n_quarters
        return {"income": quarters, "cashflow": [], "balance": []}

    def test_four_quarters_baseline(self):
        stmts = self._make_stmts(4)
        result = run_pe("technology", {}, stmts, price=100.0)
        assert result["fair_value"] is not None
        # eps=8.0, benchmark=28 → fv=224.0
        assert result["inputs_used"]["eps_ttm"] == pytest.approx(8.0)

    def test_three_quarters_gives_annualised_eps(self):
        stmts = self._make_stmts(3)
        result = run_pe("technology", {}, stmts, price=100.0)
        assert result["fair_value"] is not None
        # 3×2.0 × 4/3 = 8.0 — same as 4-quarter baseline
        assert result["inputs_used"]["eps_ttm"] == pytest.approx(8.0)

    def test_two_quarters_gives_annualised_eps(self):
        stmts = self._make_stmts(2)
        result = run_pe("technology", {}, stmts, price=100.0)
        assert result["fair_value"] is not None
        # 2×2.0 × 2 = 8.0
        assert result["inputs_used"]["eps_ttm"] == pytest.approx(8.0)
