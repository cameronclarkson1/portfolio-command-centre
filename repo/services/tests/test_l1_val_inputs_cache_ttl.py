"""
test_l1_val_inputs_cache_ttl.py — Regression tests for Cycle 6 fix L-1.

Bug (pre-fix):
    get_valuation_inputs() used CACHE_TTL["fundamentals"] (86400 s = 24 hours)
    for its cache key "val_inputs:{ticker}".  Valuation inputs include
    derived metrics that change more often than raw quarterly statements;
    a 24-hour cache caused stale inputs to persist through a user's session.

Fix:
    - Add CACHE_TTL["val_inputs"] = 3600 to config/settings.py.
    - Change the TTL reference in fundamentals_service.py from
      CACHE_TTL["fundamentals"] to CACHE_TTL["val_inputs"].

Run with:
    pytest repo/services/tests/test_l1_val_inputs_cache_ttl.py -v
"""

import sys
from pathlib import Path
import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))


class TestValInputsCacheTtlConfig:

    def test_val_inputs_key_exists_in_cache_ttl(self):
        """CACHE_TTL must include a 'val_inputs' key after the L-1 fix."""
        from config.settings import CACHE_TTL
        assert "val_inputs" in CACHE_TTL, (
            "'val_inputs' key missing from CACHE_TTL — L-1 fix not applied to settings.py"
        )

    def test_val_inputs_ttl_is_one_hour(self):
        """val_inputs TTL must be 3600 s (1 hour), not the 24-hour fundamentals value."""
        from config.settings import CACHE_TTL
        assert CACHE_TTL["val_inputs"] == 3600, (
            f"Expected 3600, got {CACHE_TTL['val_inputs']}"
        )

    def test_val_inputs_ttl_shorter_than_fundamentals(self):
        """val_inputs TTL must be shorter than the 24-hour fundamentals TTL."""
        from config.settings import CACHE_TTL
        assert CACHE_TTL["val_inputs"] < CACHE_TTL["fundamentals"], (
            "val_inputs TTL should be shorter than fundamentals — reduces stale inputs"
        )


class TestValInputsTtlUsedInService:

    def test_get_valuation_inputs_uses_val_inputs_ttl(self):
        """
        get_valuation_inputs() must use CACHE_TTL['val_inputs'], not 'fundamentals'.
        Verified by patching the cache and confirming the ttl passed to cache.set.
        """
        from unittest.mock import patch, MagicMock, call
        from config.settings import CACHE_TTL

        captured = []  # list of (key, ttl) pairs

        class FakeCache:
            def get(self, key, ttl):
                captured.append((key, ttl))
                return None  # Always miss

            def set(self, key, value, ttl):
                captured.append((key, ttl))

        with patch("services.fundamentals_service.cache", FakeCache()), \
             patch("services.fundamentals_service.get_financial_statements", return_value={}), \
             patch("services.fundamentals_service._try_providers",
                   return_value=(None, "mock", 0)):
            from services.fundamentals_service import get_valuation_inputs
            get_valuation_inputs("TEST")

        val_inputs_ttl  = CACHE_TTL["val_inputs"]
        fundamentals_ttl = CACHE_TTL["fundamentals"]

        # Find the cache call for the val_inputs key
        val_entries = [(k, t) for k, t in captured if k.startswith("val_inputs:")]
        assert val_entries, f"No cache call for 'val_inputs:*' key — calls: {captured}"

        for key, ttl in val_entries:
            assert ttl == val_inputs_ttl, (
                f"val_inputs cache key '{key}' used TTL={ttl}s — "
                f"expected {val_inputs_ttl}s (1h). L-1 fix not applied."
            )
            assert ttl != fundamentals_ttl, (
                f"val_inputs cache key '{key}' still uses fundamentals TTL "
                f"({fundamentals_ttl}s) — L-1 fix not applied to fundamentals_service.py"
            )
