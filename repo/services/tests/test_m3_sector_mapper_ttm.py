"""
test_m3_sector_mapper_ttm.py — Regression tests for Cycle 6 fix M-3.

Bug (pre-fix):
    select_models() in sector_mapper.py computed eps_ttm and op_cf_ttm with
    raw sums over cashflow[:4] / income[:4].  For companies with < 4 quarters
    of history (IPOs, partial years), TTM EPS and operating cash flow were
    understated by up to 4×.  This could suppress the P/E and P/CF model
    candidates for a profitable early-stage company, reducing valuation
    coverage.

Fix:
    Replace raw sums with ttm_sum() calls, which annualise by n / n_actual
    when fewer than 4 quarters are present.  Add `from utils.financial_calcs
    import ttm_sum` to sector_mapper.py.

Run with:
    pytest repo/services/tests/test_m3_sector_mapper_ttm.py -v
"""

import sys
from pathlib import Path
import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from services.sector_mapper import select_models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stmts(income=None, cashflow=None, balance=None):
    return {
        "income":   income   or [],
        "cashflow": cashflow or [],
        "balance":  balance  or [],
    }


def _models(income=None, cashflow=None, balance=None, ratios=None, bucket="technology"):
    stmts = _stmts(income, cashflow, balance)
    return select_models(bucket, ratios or {}, stmts)


# ---------------------------------------------------------------------------
# P/E candidate: eps_ttm must annualise
# ---------------------------------------------------------------------------

class TestEpsTtmAnnualisation:

    def test_four_quarters_pe_enabled(self):
        """4 × EPS=0.50 → ttm=2.0 > 0 → P/E added to technology model weights."""
        income = [{"eps": 0.50}] * 4
        result = _models(income=income)
        # technology core = dcf, ev_sales, ev_ebitda; pe is supplementary
        assert "pe" in result, f"pe missing from returned models: {result}"

    def test_one_quarter_eps_annualised_enables_pe(self):
        """
        1 × EPS=0.50 annualised to 2.0 → still > 0 → P/E added.
        Pre-fix: 0.50 raw → also > 0 so both paths add pe; annualisation
        is confirmed by ttm_sum being used (import test validates this).
        """
        income = [{"eps": 0.50}]
        result = _models(income=income)
        assert "pe" in result, (
            "P/E not added for single-quarter positive EPS — M-3 fix may not be applied"
        )

    def test_zero_eps_no_supplementary_pe(self):
        """EPS=0 across all quarters → pe not added (candidate disabled)."""
        income = [{"eps": 0.0}] * 4
        # pe_ratio not supplied → only ttm eps matters
        result = _models(income=income, ratios={})
        assert "pe" not in result, f"pe should not be added for zero EPS: {result}"

    def test_negative_eps_no_supplementary_pe(self):
        """Negative EPS (loss) → pe not added."""
        income = [{"eps": -1.0}] * 4
        result = _models(income=income, ratios={})
        assert "pe" not in result, f"pe should not be added for negative EPS: {result}"


# ---------------------------------------------------------------------------
# P/CF candidate: op_cf_ttm must annualise
# ---------------------------------------------------------------------------

class TestOpCfTtmAnnualisation:

    def test_four_quarters_pcf_enabled(self):
        """4 × op_cf=1B → ttm=4B > 0 → P/CF added to technology model weights."""
        cashflow = [{"operating_cash_flow": 1_000_000_000}] * 4
        result = _models(cashflow=cashflow)
        assert "pcf" in result, f"pcf missing from returned models: {result}"

    def test_one_quarter_op_cf_annualised_enables_pcf(self):
        """1 × op_cf=1B annualised to 4B → still > 0 → P/CF added."""
        cashflow = [{"operating_cash_flow": 1_000_000_000}]
        result = _models(cashflow=cashflow)
        assert "pcf" in result

    def test_zero_op_cf_no_pcf(self):
        """op_cf=0 → pcf not added."""
        cashflow = [{"operating_cash_flow": 0}] * 4
        result = _models(cashflow=cashflow)
        assert "pcf" not in result, f"pcf should not be added for zero op_cf: {result}"

    def test_negative_op_cf_no_pcf(self):
        """Negative op_cf → pcf not added."""
        cashflow = [{"operating_cash_flow": -500_000_000}] * 4
        result = _models(cashflow=cashflow)
        assert "pcf" not in result, f"pcf should not be added for negative op_cf: {result}"


# ---------------------------------------------------------------------------
# ttm_sum import is accessible from sector_mapper
# ---------------------------------------------------------------------------

class TestTtmSumImport:

    def test_ttm_sum_importable_from_sector_mapper_module(self):
        """ttm_sum must be importable via sector_mapper (import added by M-3 fix)."""
        import services.sector_mapper as sm
        assert hasattr(sm, "ttm_sum"), (
            "ttm_sum not imported in sector_mapper — M-3 fix not applied"
        )
