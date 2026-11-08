"""
test_ttm_annualisation.py — Unit tests for the _ttm annualisation fix.

Covers:
  - 4 quarters available → no annualisation (sum returned as-is)
  - 3 quarters available → sum × (4/3) annualised
  - 2 quarters available → sum × (4/2) = sum × 2
  - 1 quarter available → sum × 4
  - Edge cases: empty list, all zeros, missing field, all None, mixed None/real
  - Negative values (e.g. capex) annualise correctly

n_actual = number of quarter records in the slice, regardless of field value.
When n_actual < n (fewer than 4 quarters of data), sum is scaled up to a
full-year estimate so the DCF is not silently understated.

No live network calls — all external dependencies are stubbed.
Run with: pytest repo/services/tests/test_ttm_annualisation.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path + dependency stubs — must happen before importing
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
_stub(
    "utils.validation_utils",
    completeness_score=MagicMock(return_value=1.0),
    cross_validate=MagicMock(),
    DCF_INPUT_FIELDS=[],
)
_stub("storage.cache_manager", cache=MagicMock(get=MagicMock(return_value=None), set=MagicMock()))
_stub("config.settings", CACHE_TTL={"fundamentals": 3600, "valuation": 3600})
_stub("providers.fmp_provider")
_stub("providers.finnhub_provider")
_stub("providers.sec_edgar_provider")
_stub("providers.yfinance_provider")

# Remove any stub left by other test files so we import the real module
sys.modules.pop("services.fundamentals_service", None)

from services.fundamentals_service import _ttm  # noqa: E402


# ---------------------------------------------------------------------------
# 4 quarters — no annualisation
# ---------------------------------------------------------------------------

class TestTtmFourQuarters:
    def test_four_full_quarters_no_annualisation(self):
        quarters = [{"fcf": 100}, {"fcf": 200}, {"fcf": 300}, {"fcf": 400}]
        assert _ttm(quarters, "fcf") == 1000

    def test_four_quarters_unequal_values(self):
        quarters = [{"fcf": 50}, {"fcf": 150}, {"fcf": 200}, {"fcf": 100}]
        assert _ttm(quarters, "fcf") == 500


# ---------------------------------------------------------------------------
# 3 quarters — annualise by 4/3
# ---------------------------------------------------------------------------

class TestTtmThreeQuarters:
    def test_three_equal_quarters_annualised(self):
        quarters = [{"fcf": 100}, {"fcf": 100}, {"fcf": 100}]
        # 300 × (4/3) = 400.0
        assert _ttm(quarters, "fcf") == pytest.approx(400.0)

    def test_three_unequal_quarters_annualised(self):
        quarters = [{"fcf": 100}, {"fcf": 200}, {"fcf": 300}]
        # 600 × (4/3) = 800.0
        assert _ttm(quarters, "fcf") == pytest.approx(800.0)


# ---------------------------------------------------------------------------
# 2 quarters — annualise by 4/2 = 2
# ---------------------------------------------------------------------------

class TestTtmTwoQuarters:
    def test_two_quarters_annualised(self):
        quarters = [{"fcf": 100}, {"fcf": 200}]
        # 300 × 2 = 600.0
        assert _ttm(quarters, "fcf") == pytest.approx(600.0)

    def test_two_quarters_large_values(self):
        quarters = [{"fcf": 250_000_000}, {"fcf": 350_000_000}]
        # 600M × 2 = 1200M
        assert _ttm(quarters, "fcf") == pytest.approx(1_200_000_000.0)


# ---------------------------------------------------------------------------
# 1 quarter — annualise by 4
# ---------------------------------------------------------------------------

class TestTtmOneQuarter:
    def test_one_quarter_annualised(self):
        quarters = [{"fcf": 250_000_000}]
        # 250M × 4 = 1000M
        assert _ttm(quarters, "fcf") == pytest.approx(1_000_000_000.0)

    def test_negative_value_annualised(self):
        # Capex is typically negative in financial data
        quarters = [{"capex": -50}]
        # -50 × 4 = -200
        assert _ttm(quarters, "capex") == pytest.approx(-200.0)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestTtmEdgeCases:
    def test_empty_list_returns_zero(self):
        assert _ttm([], "fcf") == 0

    def test_all_zeros_returns_zero(self):
        quarters = [{"fcf": 0}, {"fcf": 0}, {"fcf": 0}]
        assert _ttm(quarters, "fcf") == 0

    def test_field_missing_treated_as_zero(self):
        # Quarters exist but don't contain the requested field
        quarters = [{"revenue": 100}, {"revenue": 200}]
        assert _ttm(quarters, "fcf") == 0

    def test_none_field_values_all_zero(self):
        # Field present but None → treated as 0 → total = 0
        quarters = [{"fcf": None}, {"fcf": None}, {"fcf": None}]
        assert _ttm(quarters, "fcf") == 0

    def test_mixed_none_and_real_values(self):
        # 3 quarter records; one has None FCF (treated as 0)
        # n_actual=3 (3 records), total=300, 300 × (4/3) ≈ 400
        quarters = [{"fcf": None}, {"fcf": 100}, {"fcf": 200}]
        assert _ttm(quarters, "fcf") == pytest.approx(400.0)
