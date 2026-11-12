"""
test_l2_analyst_estimates_graceful.py — Regression tests for Cycle 6 fix L-2.

Bug (pre-fix):
    get_analyst_estimates() in fmp_provider.py raised ValueError when FMP
    returned no data (tickers with no analyst coverage, international stocks,
    ETFs).  Callers that do not explicitly catch ValueError would crash.

Fix:
    Replace `raise ValueError(...)` with `return []` so callers receive an
    empty list and can handle no-coverage gracefully without try/except.

Run with:
    pytest repo/services/tests/test_l2_analyst_estimates_graceful.py -v
"""

import sys
from pathlib import Path
import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))


class TestAnalystEstimatesGraceful:

    def _call_with_empty_response(self):
        import sys
        from unittest.mock import patch
        # Clear any stub installed by test_dcf_safeguards so we get the real module.
        sys.modules.pop("providers.fmp_provider", None)
        import providers.fmp_provider as fmp
        with patch("providers.fmp_provider._get", return_value=None):
            return fmp.get_analyst_estimates("NOCOVER", limit=4)

    def test_empty_response_returns_empty_list(self):
        """No analyst data → returns [] instead of raising ValueError."""
        result = self._call_with_empty_response()
        assert result == [], (
            f"Expected empty list, got {result!r} — L-2 fix not applied"
        )

    def test_empty_response_does_not_raise(self):
        """No analyst data → must not raise any exception."""
        try:
            self._call_with_empty_response()
        except ValueError as e:
            pytest.fail(f"ValueError still raised: {e} — L-2 fix not applied")
        except Exception as e:
            pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")

    def test_empty_list_response_returns_empty_list(self):
        """FMP returning [] (not None) → also returns empty list."""
        import sys
        from unittest.mock import patch
        sys.modules.pop("providers.fmp_provider", None)
        import providers.fmp_provider as fmp
        with patch("providers.fmp_provider._get", return_value=[]):
            result = fmp.get_analyst_estimates("NOCOVER", limit=4)
        assert result == []

    def test_valid_response_still_parsed(self):
        """Normal data path still works — fix must not break existing behaviour."""
        import sys
        from unittest.mock import patch
        sys.modules.pop("providers.fmp_provider", None)
        import providers.fmp_provider as fmp
        fake_data = [{
            "date":               "2025-12-31",
            "estimatedRevenueLow":  90e9,
            "estimatedRevenueHigh": 100e9,
            "estimatedRevenueavg":  95e9,
            "estimatedEpsLow":      5.0,
            "estimatedEpsHigh":     6.0,
            "estimatedEpsAvg":      5.5,
        }]
        with patch("providers.fmp_provider._get", return_value=fake_data):
            result = fmp.get_analyst_estimates("AAPL", limit=4)
        assert len(result) >= 1
        assert result[0].get("period") is not None or result[0].get("date") is not None
