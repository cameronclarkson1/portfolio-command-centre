"""
test_h3_fcf_per_share.py — Regression tests for Cycle 6 fix H-3.

Bug (pre-fix):
    _fcf_ttm in get_key_ratios() used a raw sum:
        sum(q.get("free_cash_flow") or 0 for q in _cashflow[:4])
    For companies with < 4 quarters of cashflow history (IPOs, partial years),
    this understated FCF by up to 4×, producing a FCF/Share ratio far below
    the true annualised value.

Fix:
    Replace the raw sum with ttm_sum(_cashflow, "free_cash_flow"), which
    annualises by n / n_actual when fewer than n (4) quarters are present.
    ttm_sum is already imported in fundamentals_service.py.

Run with:
    pytest repo/services/tests/test_h3_fcf_per_share.py -v
"""

import sys
from pathlib import Path
import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from utils.financial_calcs import ttm_sum


# ---------------------------------------------------------------------------
# Verify ttm_sum behaviour used by the H-3 fix
# ---------------------------------------------------------------------------

class TestTtmSumForFcf:

    def test_four_quarters_no_scaling(self):
        """4 × 500 → 2000 (no annualisation needed)."""
        quarters = [{"free_cash_flow": 500}] * 4
        assert ttm_sum(quarters, "free_cash_flow") == pytest.approx(2000.0)

    def test_three_quarters_annualised(self):
        """3 × 500 = 1500 raw → annualised 2000."""
        quarters = [{"free_cash_flow": 500}] * 3
        assert ttm_sum(quarters, "free_cash_flow") == pytest.approx(2000.0)

    def test_two_quarters_annualised(self):
        quarters = [{"free_cash_flow": 500}] * 2
        assert ttm_sum(quarters, "free_cash_flow") == pytest.approx(2000.0)

    def test_one_quarter_annualised(self):
        quarters = [{"free_cash_flow": 500}] * 1
        assert ttm_sum(quarters, "free_cash_flow") == pytest.approx(2000.0)

    def test_zero_fcf_returns_zero(self):
        quarters = [{"free_cash_flow": 0}] * 4
        assert ttm_sum(quarters, "free_cash_flow") == 0

    def test_all_none_fcf_returns_zero(self):
        quarters = [{"free_cash_flow": None}] * 4
        assert ttm_sum(quarters, "free_cash_flow") == 0

    def test_missing_field_returns_zero(self):
        quarters = [{}] * 4
        assert ttm_sum(quarters, "free_cash_flow") == 0

    def test_empty_list_returns_zero(self):
        assert ttm_sum([], "free_cash_flow") == 0

    def test_negative_fcf_annualised(self):
        """Negative FCF is valid and must annualise correctly."""
        quarters = [{"free_cash_flow": -300}] * 2
        assert ttm_sum(quarters, "free_cash_flow") == pytest.approx(-1200.0)


# ---------------------------------------------------------------------------
# Integration smoke test: get_key_ratios produces an annualised fcf_per_share
# ---------------------------------------------------------------------------

class TestFcfPerShareAnnualisation:

    def _build_ratios(self, cashflow_quarters, ticker, income_quarters=None):
        from services.fundamentals_service import get_key_ratios
        from unittest.mock import patch, MagicMock

        shares = 1_000_000_000  # 1B shares
        if income_quarters is None:
            income_quarters = [{"shares_diluted": shares}] * 4

        fake_statements = {
            "income":   income_quarters,
            "cashflow": cashflow_quarters,
            "balance":  [{"total_debt": 0, "total_equity": 1e9}],
        }

        # _try_providers returns (data, provider_name, latency) tuples
        def fake_try_providers(specs, label):
            name = specs[0][0] if specs else "mock"
            if "key metrics" in label:
                return ([{"pe_ratio": 20.0}], name, 0)
            return ({}, name, 0)

        with patch("services.fundamentals_service.get_financial_statements",
                   return_value=fake_statements), \
             patch("services.fundamentals_service._try_providers",
                   side_effect=fake_try_providers), \
             patch("services.fundamentals_service.cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set.return_value = None
            return get_key_ratios(ticker)

    def test_four_quarters_fcf_per_share(self):
        """4 × $500M FCF / 1B shares = $2.00/share."""
        quarters = [{"free_cash_flow": 500_000_000}] * 4
        result = self._build_ratios(quarters, "TESTA")
        assert result is not None
        assert result.get("fcf_per_share") == pytest.approx(2.0, rel=1e-3)

    def test_one_quarter_annualised_fcf_per_share(self):
        """
        1 × $500M FCF annualised = $2B / 1B shares = $2.00/share.
        Pre-fix would give $500M / 1B = $0.50/share (4× understated).
        """
        quarters = [{"free_cash_flow": 500_000_000}]
        result = self._build_ratios(quarters, "TESTB")
        assert result is not None
        assert result.get("fcf_per_share") == pytest.approx(2.0, rel=1e-3), (
            "fcf_per_share is not annualised — H-3 fix not applied"
        )

    def test_two_quarters_matches_four_quarter_equivalent(self):
        """2 × $500M quarters (annualised) must equal 4 × $500M full year."""
        q_two  = [{"free_cash_flow": 500_000_000}] * 2
        q_four = [{"free_cash_flow": 500_000_000}] * 4
        r_two  = self._build_ratios(q_two,  "TESTC")
        r_four = self._build_ratios(q_four, "TESTD")
        assert r_two["fcf_per_share"] == pytest.approx(r_four["fcf_per_share"], rel=1e-3)
