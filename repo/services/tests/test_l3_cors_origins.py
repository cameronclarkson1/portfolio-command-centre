"""
test_l3_cors_origins.py — Regression tests for Cycle 6 fix L-3.

Bug (pre-fix):
    api/main.py hardcoded allow_origins=["*"] in CORSMiddleware.  The wildcard
    allows any origin, which is acceptable for local dev but risky once the
    API is deployed behind a known frontend domain — an env var cannot restrict it.

Fix:
    Read CORS_ALLOW_ORIGIN from the environment.  If set, parse it as a
    comma-separated list of allowed origins.  If unset, fall back to ["*"]
    so local dev is unaffected.

Run with:
    pytest repo/services/tests/test_l3_cors_origins.py -v

Note: these tests import _cors_origins after patching os.environ, so they
re-import the computed list from the module.  Since main.py runs the
computation at module load time, we reload it for each scenario.
"""

import sys
import os
import importlib
from pathlib import Path
import pytest

# api/ must be on sys.path so `import main` resolves.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
API_DIR      = PROJECT_ROOT / "api"
REPO_DIR     = PROJECT_ROOT / "repo"
for d in [str(API_DIR), str(REPO_DIR)]:
    if d not in sys.path:
        sys.path.insert(0, d)


def _load_cors_origins(env_value: str | None) -> list[str]:
    """Reload api.main with the given CORS_ALLOW_ORIGIN env value and return _cors_origins."""
    old = os.environ.get("CORS_ALLOW_ORIGIN")
    try:
        if env_value is None:
            os.environ.pop("CORS_ALLOW_ORIGIN", None)
        else:
            os.environ["CORS_ALLOW_ORIGIN"] = env_value
        import main
        importlib.reload(main)
        return main._cors_origins
    finally:
        if old is None:
            os.environ.pop("CORS_ALLOW_ORIGIN", None)
        else:
            os.environ["CORS_ALLOW_ORIGIN"] = old


class TestCorsOrigins:

    def test_no_env_var_defaults_to_wildcard(self):
        """CORS_ALLOW_ORIGIN unset → allow_origins = ['*'] (local dev default)."""
        origins = _load_cors_origins(None)
        assert origins == ["*"], f"Expected ['*'], got {origins}"

    def test_single_origin_set(self):
        """Single origin → allow_origins = [that origin]."""
        origins = _load_cors_origins("https://app.example.com")
        assert origins == ["https://app.example.com"], f"Got {origins}"

    def test_multiple_origins_comma_separated(self):
        """Comma-separated origins → list of stripped strings."""
        origins = _load_cors_origins(
            "https://app.example.com, https://staging.example.com"
        )
        assert "https://app.example.com"     in origins
        assert "https://staging.example.com" in origins
        assert len(origins) == 2

    def test_wildcard_not_in_origins_when_env_set(self):
        """When env var is set to specific origins, '*' must NOT be in the list."""
        origins = _load_cors_origins("https://app.example.com")
        assert "*" not in origins, (
            "Wildcard '*' still present when CORS_ALLOW_ORIGIN is explicitly set — "
            "L-3 fix not applied"
        )

    def test_empty_env_var_defaults_to_wildcard(self):
        """CORS_ALLOW_ORIGIN='' (empty string) → fall back to ['*']."""
        origins = _load_cors_origins("")
        assert origins == ["*"], f"Empty env var should give ['*'], got {origins}"

    def test_whitespace_entries_stripped(self):
        """Entries with leading/trailing whitespace are stripped."""
        origins = _load_cors_origins("  https://a.com  ,  https://b.com  ")
        assert "https://a.com" in origins
        assert "https://b.com" in origins
        for o in origins:
            assert o == o.strip(), f"Origin not stripped: {o!r}"
