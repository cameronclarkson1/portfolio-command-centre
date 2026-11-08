"""
test_dcf_safeguards.py — Production DCF safeguard tests for repo/services/.

Covers:
  - Negative, zero, None, NaN, non-numeric FCF rejected at input guard
  - Non-positive equity value rejected before per-share calculation
  - Valid positive DCF runs end-to-end correctly (with and without FCF margin method)
  - Negative, zero, NaN, ±inf, non-numeric fair values excluded from _blend_results
  - Weight renormalisation after model exclusion
  - fair_value_low is always positive (no negative range endpoints)
  - Insufficient-data path when all models are invalid
  - Regression profiles for ORCL and SMCI (known negative-FCF snapshots)

No live network calls — all external dependencies are stubbed at module level.
Run with: pytest repo/services/tests/test_dcf_safeguards.py -v
"""

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path + dependency stubs — must happen before importing the modules under test
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


_BUCKET_WEIGHTS = {"technology": {"dcf": 0.40, "pe": 0.35, "ev_ebitda": 0.25}}

_stub(
    "utils.logging_utils",
    get_logger=lambda _: _logger_inst,
    log_cache_hit=MagicMock(),
    log_cache_miss=MagicMock(),
)
_stub(
    "services.fundamentals_service",
    get_valuation_inputs=MagicMock(),
    get_key_ratios=MagicMock(),
    get_financial_statements=MagicMock(),
)
_stub(
    "services.sector_mapper",
    get_bucket=MagicMock(return_value="technology"),
    is_early_stage=MagicMock(return_value=False),
    select_models=MagicMock(return_value={"dcf": 0.40, "pe": 0.35, "ev_ebitda": 0.25}),
    BUCKET_WEIGHTS=_BUCKET_WEIGHTS,
    BUCKET_LABELS={},
    BUCKET_EXPLANATIONS={},
)
_stub("services.relative_valuation")
_stub("services.ddm_model")
_stub("services.reit_valuation")
_stub(
    "storage.cache_manager",
    cache=MagicMock(get=MagicMock(return_value=None), set=MagicMock()),
)
_stub("config.settings", CACHE_TTL={"valuation": 3600, "fundamentals": 3600})
_stub("providers.fmp_provider")

from services.dcf_model import run_dcf                    # noqa: E402
from services.valuation_engine import _blend_results      # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_inputs(**overrides) -> dict:
    """Minimal valid inputs for a healthy company (no analyst estimates → raw FCF fallback)."""
    base = {
        "free_cash_flow":        500_000_000,   # $500M positive FCF
        "shares_out":            500_000_000,   # 500M shares
        "revenue_growth":        0.10,
        "wacc_estimate":         0.09,
        "net_debt":              0,
        "revenue_ttm":           None,          # no margin method by default
        "analyst_rev_growth_y1": None,
        "analyst_rev_growth_y2": None,
        "analyst_count":         0,
        "analyst_estimate_spread": None,
        "completeness":          1.0,
        "warnings":              [],
    }
    base.update(overrides)
    return base


def _base_inputs_with_margin(**overrides) -> dict:
    """Valid inputs with both FCF and revenue_ttm → activates margin method."""
    base = _base_inputs(
        free_cash_flow=5_000_000_000,   # $5B FCF
        revenue_ttm=50_000_000_000,     # $50B revenue → 10% margin (valid range)
        shares_out=1_000_000_000,
    )
    base.update(overrides)
    return base


TECH_BUCKET = "technology"
TECH_WEIGHTS = {"dcf": 0.40, "pe": 0.35, "ev_ebitda": 0.25}


def _model(fv, confidence: float = 65.0) -> dict:
    return {"fair_value": fv, "confidence": confidence, "warnings": []}


# ---------------------------------------------------------------------------
# DCF input-guard: missing / malformed inputs → missing_inputs
# ---------------------------------------------------------------------------

def test_zero_fcf_returns_missing_inputs():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow=0))
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "missing_inputs"


def test_none_fcf_returns_missing_inputs():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow=None))
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "missing_inputs"


def test_none_shares_returns_missing_inputs():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(shares_out=None))
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "missing_inputs"


def test_zero_shares_returns_missing_inputs():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(shares_out=0))
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "missing_inputs"


def test_nan_fcf_returns_missing_inputs():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow=float("nan")))
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "missing_inputs"


def test_inf_fcf_returns_missing_inputs():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow=float("inf")))
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "missing_inputs"


def test_string_fcf_returns_missing_inputs():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow="not_a_number"))
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "missing_inputs"


def test_list_fcf_returns_missing_inputs():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow=[500_000_000]))
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "missing_inputs"


# ---------------------------------------------------------------------------
# DCF input-guard: negative FCF → negative_fcf
# ---------------------------------------------------------------------------

def test_negative_fcf_returns_unavailable():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow=-50_000_000))
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "negative_fcf"


def test_negative_fcf_warning_contains_reason():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow=-50_000_000))
    combined = " ".join(result.get("warnings", []))
    assert "negative" in combined.lower()


def test_negative_fcf_warning_includes_dollar_amount():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow=-86_150_000))
    combined = " ".join(result.get("warnings", []))
    assert "-86." in combined


def test_negative_fcf_inputs_used_records_fcf():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow=-50_000_000))
    assert result["inputs_used"].get("free_cash_flow") == -50_000_000


def test_small_negative_fcf_also_rejected():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs(free_cash_flow=-1))
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "negative_fcf"


# ---------------------------------------------------------------------------
# DCF equity-value guard: non-positive equity → non_positive_equity_value
# ---------------------------------------------------------------------------

def test_large_net_debt_returns_non_positive_equity():
    result = run_dcf(
        "TEST", TECH_BUCKET,
        inputs=_base_inputs(
            free_cash_flow=1_000_000,     # tiny FCF → tiny EV
            net_debt=10_000_000_000,      # $10B net debt
        ),
    )
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "non_positive_equity_value"


def test_massive_net_debt_returns_non_positive_equity():
    result = run_dcf(
        "TEST", TECH_BUCKET,
        inputs=_base_inputs(
            free_cash_flow=1_000_000,
            net_debt=100_000_000_000,     # $100B
        ),
    )
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "non_positive_equity_value"


def test_non_positive_equity_returns_partial_inputs_used():
    result = run_dcf(
        "TEST", TECH_BUCKET,
        inputs=_base_inputs(free_cash_flow=1_000_000, net_debt=10_000_000_000),
    )
    iu = result.get("inputs_used", {})
    assert "fcf_ttm" in iu
    assert "net_debt" in iu
    assert "shares_out" in iu


def test_non_positive_equity_warning_contains_equity():
    result = run_dcf(
        "TEST", TECH_BUCKET,
        inputs=_base_inputs(free_cash_flow=1_000_000, net_debt=10_000_000_000),
    )
    combined = " ".join(result.get("warnings", []))
    assert "equity" in combined.lower()


# ---------------------------------------------------------------------------
# Valid positive DCF — raw-FCF fallback path (no revenue_ttm)
# ---------------------------------------------------------------------------

def test_positive_fcf_returns_positive_fair_value():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs())
    assert result["fair_value"] is not None
    assert result["fair_value"] > 0


def test_fair_value_is_finite():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs())
    assert math.isfinite(result["fair_value"])


def test_confidence_in_valid_range():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs())
    assert 0 < result["confidence"] <= 100


def test_model_key_is_dcf():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs())
    assert result["model"] == "dcf"


def test_inputs_used_populated_on_success():
    result = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs())
    iu = result.get("inputs_used", {})
    for key in ("fcf_ttm", "g_y1", "wacc", "net_debt", "shares_out"):
        assert key in iu, f"inputs_used missing '{key}'"


# ---------------------------------------------------------------------------
# Valid positive DCF — FCF margin method path (revenue_ttm provided)
# ---------------------------------------------------------------------------

def test_margin_method_produces_positive_fair_value():
    result = run_dcf("MSFT", TECH_BUCKET, inputs=_base_inputs_with_margin())
    assert result["fair_value"] is not None
    assert result["fair_value"] > 0


def test_margin_method_populates_fcf_margin():
    result = run_dcf("MSFT", TECH_BUCKET, inputs=_base_inputs_with_margin())
    iu = result.get("inputs_used", {})
    assert iu.get("fcf_margin") is not None
    assert 0.01 <= iu["fcf_margin"] <= 0.60


def test_analyst_estimates_improve_confidence():
    """Adding analyst estimates should raise confidence vs no estimates."""
    base   = run_dcf("TEST", TECH_BUCKET, inputs=_base_inputs_with_margin())
    with_a = run_dcf(
        "TEST", TECH_BUCKET,
        inputs=_base_inputs_with_margin(
            analyst_rev_growth_y1=0.12,
            analyst_rev_growth_y2=0.10,
            analyst_count=12,
        ),
    )
    assert with_a["fair_value"] is not None and with_a["fair_value"] > 0
    assert with_a["confidence"] >= base["confidence"]


# ---------------------------------------------------------------------------
# _blend_results: invalid fair values must be excluded
# ---------------------------------------------------------------------------

def test_negative_fv_excluded_from_blend():
    models = {
        "dcf":      _model(-325.2, 20.0),
        "pe":       _model(159.19, 65.0),
        "ev_ebitda": _model(168.56, 63.0),
    }
    result = _blend_results(models, TECH_WEIGHTS, 126.41)
    assert result["fair_value_base"] is not None
    assert result["fair_value_base"] > 0


def test_none_fv_excluded_from_blend():
    models = {
        "dcf": _model(None, 20.0),
        "pe":  _model(159.19, 65.0),
    }
    result = _blend_results(models, TECH_WEIGHTS, 100.0)
    assert result["fair_value_base"] is not None
    assert result["fair_value_base"] > 0


def test_nan_fv_excluded_from_blend():
    models = {
        "dcf": _model(float("nan"), 20.0),
        "pe":  _model(100.0, 65.0),
    }
    result = _blend_results(models, {"dcf": 0.5, "pe": 0.5}, 90.0)
    assert result["fair_value_base"] is not None
    assert math.isfinite(result["fair_value_base"])


def test_inf_fv_excluded_from_blend():
    models = {
        "dcf": _model(float("inf"), 20.0),
        "pe":  _model(100.0, 65.0),
    }
    result = _blend_results(models, {"dcf": 0.5, "pe": 0.5}, 90.0)
    assert result["fair_value_base"] is not None
    assert math.isfinite(result["fair_value_base"])


def test_neg_inf_fv_excluded_from_blend():
    models = {
        "dcf": _model(float("-inf"), 20.0),
        "pe":  _model(100.0, 65.0),
    }
    result = _blend_results(models, {"dcf": 0.5, "pe": 0.5}, 90.0)
    assert result["fair_value_base"] is not None
    assert math.isfinite(result["fair_value_base"])


def test_zero_fv_excluded_from_blend():
    models = {
        "dcf": _model(0.0, 20.0),
        "pe":  _model(100.0, 65.0),
    }
    result = _blend_results(models, {"dcf": 0.5, "pe": 0.5}, 90.0)
    assert result["fair_value_base"] is not None
    assert result["fair_value_base"] > 0


def test_string_fv_excluded_from_blend():
    models = {
        "dcf": _model("not_a_number", 20.0),
        "pe":  _model(100.0, 65.0),
    }
    result = _blend_results(models, {"dcf": 0.5, "pe": 0.5}, 90.0)
    assert result["fair_value_base"] is not None
    assert result["fair_value_base"] > 0


# ---------------------------------------------------------------------------
# fair_value_low is always positive (no negative range endpoints)
# ---------------------------------------------------------------------------

def test_fair_value_low_is_positive_when_negative_dcf_present():
    """The range minimum must exclude negative DCF values."""
    models = {
        "dcf":      _model(-325.2, 20.0),
        "pe":       _model(159.19, 65.0),
        "ev_ebitda": _model(168.56, 63.0),
    }
    result = _blend_results(models, TECH_WEIGHTS, 126.41)
    assert result["fair_value_low"] is not None
    assert result["fair_value_low"] > 0


def test_fair_value_low_is_minimum_of_positive_models():
    models = {
        "dcf": _model(80.0, 60.0),
        "pe":  _model(120.0, 65.0),
    }
    result = _blend_results(models, {"dcf": 0.5, "pe": 0.5}, 100.0)
    assert result["fair_value_low"] == pytest.approx(80.0, abs=0.01)
    assert result["fair_value_high"] == pytest.approx(120.0, abs=0.01)


# ---------------------------------------------------------------------------
# All models invalid → Insufficient data
# ---------------------------------------------------------------------------

def test_all_invalid_models_returns_insufficient_data():
    models = {
        "dcf": _model(None),
        "pe":  _model(-50.0),
        "ev_ebitda": _model(float("nan")),
    }
    result = _blend_results(models, TECH_WEIGHTS, 100.0)
    assert result["fair_value_base"] is None
    assert result["valuation_rating"] == "Insufficient data"
    assert result["overall_confidence"] == 0.0


def test_empty_models_dict_returns_insufficient_data():
    result = _blend_results({}, {}, 100.0)
    assert result["fair_value_base"] is None
    assert result["valuation_rating"] == "Insufficient data"


# ---------------------------------------------------------------------------
# Weight renormalisation
# ---------------------------------------------------------------------------

def test_weights_sum_to_one_when_model_excluded():
    models = {
        "dcf": _model(None),     # excluded
        "pe":  _model(150.0),
        "ev_ebitda": _model(160.0),
    }
    result = _blend_results(models, TECH_WEIGHTS, 140.0)
    wu = result["weights_used"]
    assert abs(sum(wu.values()) - 1.0) < 1e-9
    assert "dcf" not in wu


def test_weights_sum_to_one_all_models_valid():
    models = {
        "dcf":      _model(100.0),
        "pe":       _model(120.0),
        "ev_ebitda": _model(110.0),
    }
    result = _blend_results(models, TECH_WEIGHTS, 100.0)
    wu = result["weights_used"]
    assert abs(sum(wu.values()) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Regression profiles — ORCL and SMCI (known negative-FCF snapshots)
# ---------------------------------------------------------------------------

def test_orcl_negative_dcf_excluded_from_blend():
    """ORCL Jul-2026 snapshot: DCF returned -325.20 due to negative FCF."""
    models = {
        "dcf":      _model(-325.20, 20.0),
        "pe":       _model(159.19,  65.0),
        "ev_ebitda": _model(168.56, 63.0),
    }
    result = _blend_results(models, TECH_WEIGHTS, 126.41)
    assert result["fair_value_base"] is not None and result["fair_value_base"] > 0
    assert result["fair_value_low"]  is not None and result["fair_value_low"]  > 0
    assert "dcf" not in result["weights_used"]


def test_smci_negative_dcf_excluded_from_blend():
    """SMCI Jul-2026 snapshot: DCF returned -503.90 due to negative FCF."""
    models = {
        "dcf":      _model(-503.90, 20.0),
        "pe":       _model(37.20,   65.0),
        "ev_ebitda": _model(23.58,  63.0),
    }
    result = _blend_results(models, TECH_WEIGHTS, 24.18)
    assert result["fair_value_base"] is not None and result["fair_value_base"] > 0
    assert result["fair_value_low"]  is not None and result["fair_value_low"]  > 0
    assert "dcf" not in result["weights_used"]


def test_orcl_negative_fcf_blocked_at_dcf_model():
    """Verify run_dcf itself blocks negative FCF before computing anything."""
    result = run_dcf(
        "ORCL", TECH_BUCKET,
        inputs=_base_inputs(free_cash_flow=-1_950_000_000),  # ORCL-like TTM FCF
    )
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "negative_fcf"


def test_smci_negative_fcf_blocked_at_dcf_model():
    result = run_dcf(
        "SMCI", TECH_BUCKET,
        inputs=_base_inputs(free_cash_flow=-812_000_000),
    )
    assert result["fair_value"] is None
    assert result.get("unavailable_reason") == "negative_fcf"
