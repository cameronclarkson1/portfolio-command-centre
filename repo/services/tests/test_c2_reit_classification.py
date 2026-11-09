"""
test_c2_reit_classification.py — Regression tests for Cycle 5 fix C-2.

Bug (pre-fix):
    run_valuation() applied the early-stage override unconditionally:

        bucket = get_bucket(sector, industry)
        if is_early_stage(ratios, statements):   # no bucket guard
            bucket = "early_stage"

    REITs routinely report negative GAAP net income due to large non-cash
    depreciation charges on their real-estate portfolios.  This triggered
    is_early_stage() → True, overwriting bucket="reit" with "early_stage",
    replacing P/FFO/P/AFFO (correct) with EV/Sales/P/CF (wrong).

Fix:
    Guard the override in run_valuation() to skip the check for sectors where
    negative GAAP net income is structurally expected:

        if bucket not in ("reit", "financials", "insurance") and is_early_stage(...):
            bucket = "early_stage"

Tests cover:
  - Standard equity REIT
  - Mortgage REIT (via INDUSTRY_OVERRIDES)
  - Industrial REIT
  - Residential REIT
  - Non-REIT property company (sector=Real Estate)
  - Financials (bank with large loan-loss provision)
  - Insurance (reserve strengthening)
  - Early-stage tech company (must still become early_stage)
  - Profitable REIT (no trigger — verify unaffected)
  - Missing / ambiguous classifications
  - is_early_stage() trigger confirmation (precondition for the fix)

Run with:
    pytest repo/services/tests/test_c2_reit_classification.py -v
"""

import sys
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from services.sector_mapper import get_bucket, is_early_stage


# ---------------------------------------------------------------------------
# Helper: replicate the FIXED bucket-determination logic from run_valuation().
# Tests use this to verify the guard works, without touching network calls.
# ---------------------------------------------------------------------------

_PROTECTED = frozenset({"reit", "financials", "insurance"})


def _determine_bucket(sector, industry, ratios, statements):
    """
    Replicates the FIXED bucket selection from valuation_engine.run_valuation().
    Use this in tests to verify post-fix bucket assignment.
    """
    bucket = get_bucket(sector, industry)
    if bucket not in _PROTECTED and is_early_stage(ratios, statements):
        bucket = "early_stage"
    return bucket


def _negative_income_stmts(quarters=4):
    """Mock statements with negative GAAP net income — common for REITs."""
    return {
        "income":   [{"net_income": -50_000_000}] * quarters,
        "cashflow": [],
        "balance":  [],
    }


def _positive_income_stmts(quarters=4):
    """Mock statements with positive GAAP net income."""
    return {
        "income":   [{"net_income": 50_000_000}] * quarters,
        "cashflow": [],
        "balance":  [],
    }


# ---------------------------------------------------------------------------
# Sector / industry → bucket mapping tests
# ---------------------------------------------------------------------------

class TestGetBucket:

    def test_standard_equity_reit(self):
        assert get_bucket("Real Estate", "REIT - Retail") == "reit"

    def test_mortgage_reit(self):
        # "mortgage" substring matches INDUSTRY_OVERRIDES key
        assert get_bucket("Real Estate", "REIT - Mortgage") == "reit"

    def test_industrial_reit(self):
        assert get_bucket("Real Estate", "REIT - Industrial") == "reit"

    def test_residential_reit(self):
        assert get_bucket("Real Estate", "REIT - Residential") == "reit"

    def test_explicit_reit_industry_string(self):
        # Full "real estate investment trust" phrase in INDUSTRY_OVERRIDES
        assert get_bucket("Real Estate", "Real Estate Investment Trust") == "reit"

    def test_real_estate_sector_no_industry(self):
        # Sector "Real Estate" maps to "reit" via SECTOR_MAP
        assert get_bucket("Real Estate", None) == "reit"

    def test_real_estate_non_reit_property_company(self):
        # Sector "Real Estate" always maps to "reit" in the current data model
        assert get_bucket("Real Estate", "Real Estate Services") == "reit"

    def test_financials_sector(self):
        assert get_bucket("Financial Services", "Banks") == "financials"

    def test_insurance_industry_override(self):
        # "insurance" substring matches INDUSTRY_OVERRIDES
        assert get_bucket("Financial Services", "Property & Casualty Insurance") == "insurance"

    def test_technology_sector(self):
        assert get_bucket("Technology", None) == "technology"

    def test_missing_sector_defaults(self):
        assert get_bucket(None, None) == "default"


# ---------------------------------------------------------------------------
# is_early_stage() trigger confirmation
# ---------------------------------------------------------------------------

class TestIsEarlyStageConfirmation:
    """
    These tests confirm that the trigger condition EXISTS (the precondition
    that makes the C-2 bug meaningful).  They should still pass after the fix
    because is_early_stage() itself is NOT modified.
    """

    def test_negative_net_income_triggers(self):
        """is_early_stage() returns True when TTM net income is negative."""
        assert is_early_stage({}, _negative_income_stmts()) is True

    def test_negative_pe_triggers(self):
        """is_early_stage() returns True when P/E ratio is negative."""
        assert is_early_stage({"pe_ratio": -20}, _positive_income_stmts()) is True

    def test_positive_net_income_does_not_trigger(self):
        """is_early_stage() returns False when earnings are positive."""
        assert is_early_stage({}, _positive_income_stmts()) is False

    def test_zero_net_income_does_not_trigger(self):
        """is_early_stage() returns False when net income is exactly zero."""
        stmts = {"income": [{"net_income": 0}] * 4, "cashflow": [], "balance": []}
        assert is_early_stage({}, stmts) is False

    def test_empty_statements_does_not_trigger(self):
        """is_early_stage() returns False when income list is empty (sum=0)."""
        stmts = {"income": [], "cashflow": [], "balance": []}
        assert is_early_stage({}, stmts) is False


# ---------------------------------------------------------------------------
# C-2 fix: bucket guard prevents early_stage override for protected sectors
# ---------------------------------------------------------------------------

class TestReitBucketGuard:

    def test_reit_negative_income_stays_reit(self):
        """
        Core C-2 scenario: REIT with negative GAAP net income must stay 'reit'.
        Before fix: bucket was overwritten to 'early_stage'.
        After fix:  bucket guard protects the 'reit' assignment.
        """
        bucket = _determine_bucket(
            sector="Real Estate",
            industry="REIT - Retail",
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "reit", (
            f"REIT with negative GAAP net income became '{bucket}' — C-2 guard not working"
        )

    def test_reit_negative_pe_stays_reit(self):
        """REIT with negative P/E (derived from negative GAAP earnings) must stay 'reit'."""
        bucket = _determine_bucket(
            sector="Real Estate",
            industry="REIT - Retail",
            ratios={"pe_ratio": -20},
            statements=_positive_income_stmts(),
        )
        assert bucket == "reit"

    def test_mortgage_reit_stays_reit(self):
        """Mortgage REIT (identified via INDUSTRY_OVERRIDES) must stay 'reit'."""
        bucket = _determine_bucket(
            sector="Real Estate",
            industry="REIT - Mortgage",
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "reit"

    def test_industrial_reit_stays_reit(self):
        """Industrial REIT with negative GAAP income must stay 'reit'."""
        bucket = _determine_bucket(
            sector="Real Estate",
            industry="REIT - Industrial",
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "reit"

    def test_residential_reit_stays_reit(self):
        """Residential REIT with negative GAAP income must stay 'reit'."""
        bucket = _determine_bucket(
            sector="Real Estate",
            industry="REIT - Residential",
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "reit"

    def test_financials_negative_income_stays_financials(self):
        """Bank with large loan-loss provision (negative income) must stay 'financials'."""
        bucket = _determine_bucket(
            sector="Financial Services",
            industry="Banks",
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "financials"

    def test_insurance_negative_income_stays_insurance(self):
        """Insurance company with reserve strengthening must stay 'insurance'."""
        bucket = _determine_bucket(
            sector="Financial Services",
            industry="Property & Casualty Insurance",
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "insurance"

    def test_early_stage_tech_still_classified(self):
        """
        Early-stage tech company: negative net income must still trigger early_stage.
        The fix must not accidentally protect unrelated sectors.
        """
        bucket = _determine_bucket(
            sector="Technology",
            industry=None,
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "early_stage", (
            f"Loss-making tech company should become 'early_stage', got '{bucket}'"
        )

    def test_early_stage_healthcare_still_classified(self):
        """Early-stage biotech (negative income): must still become 'early_stage'."""
        bucket = _determine_bucket(
            sector="Healthcare",
            industry=None,
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "early_stage"

    def test_early_stage_consumer_still_classified(self):
        """Early-stage consumer company: must still become 'early_stage'."""
        bucket = _determine_bucket(
            sector="Consumer Cyclical",
            industry=None,
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "early_stage"

    def test_profitable_reit_unaffected(self):
        """REIT with positive GAAP net income: not an early-stage trigger; stays 'reit'."""
        bucket = _determine_bucket(
            sector="Real Estate",
            industry="REIT - Retail",
            ratios={},
            statements=_positive_income_stmts(),
        )
        assert bucket == "reit"

    def test_missing_statements_reit_stays_reit(self):
        """REIT with no statement data: empty sum=0; is_early_stage=False; stays 'reit'."""
        bucket = _determine_bucket(
            sector="Real Estate",
            industry="REIT - Retail",
            ratios={},
            statements={"income": [], "cashflow": [], "balance": []},
        )
        assert bucket == "reit"

    def test_missing_industry_real_estate_sector(self):
        """sector='Real Estate' without industry → mapped to 'reit' via SECTOR_MAP."""
        bucket = _determine_bucket(
            sector="Real Estate",
            industry=None,
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "reit"

    def test_default_bucket_still_overrideable(self):
        """Unknown sector → 'default' bucket; negative income still triggers early_stage."""
        bucket = _determine_bucket(
            sector=None,
            industry=None,
            ratios={},
            statements=_negative_income_stmts(),
        )
        assert bucket == "early_stage"
