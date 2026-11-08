# Development Backlog — Portfolio Command Centre

This file is the persistent task list for autonomous development cycles.
Read it at the start of every cycle. Update it as tasks are started, completed, or discovered.

---

## In Progress

*(nothing currently in progress — start here)*

---

## Ready (approved, unblocked)

### [BUG] `_ttm` missing-quarter bias in fundamentals_service
**File:** `repo/services/fundamentals_service.py` — `_ttm()` helper  
**Problem:** Missing quarters are summed as $0 rather than annualised. A company reporting
3 quarters has its TTM FCF understated by 25%, biasing DCF fair values downward.  
**Fix:** When `n_actual < n`, multiply sum by `4 / n_actual` to annualise.  
**Risk:** Low — improves accuracy for companies with incomplete quarterly history.  
**Tests required:** Unit test covering 1, 2, 3, and 4 quarters available.

### [BUG] Cross-validation truthiness for relative models (`frontend/services/`)
**File:** `frontend/services/valuation_engine.py` line 228  
**Problem:** `relative_keys` filter uses `v.get("fair_value")` truthiness — same bug already
fixed in `repo/` but not yet applied to the Streamlit frontend copy.  
**Fix:** Apply same `isinstance + isfinite + > 0` check as `repo/valuation_engine.py:259-266`.  
**Risk:** Very low — `frontend/` is not production-deployed.

### [DEBT] `run_dcf_model` dead code in `valuation_service.py`
**Files:** `frontend/services/valuation_service.py`, `repo/services/valuation_service.py`  
**Problem:** `run_dcf_model` is defined in both but called from nowhere. Contains stale bugs
(truthiness FCF guard, no equity guard) that could confuse future developers.  
**Fix:** Delete the function from both files. Confirm `_save_valuation_to_db` is not called
elsewhere before removing. Add a note to CLAUDE.md if DB schema changes are needed.  
**Risk:** Low — confirmed dead code (no importers found).

---

## Needs Approval (do not implement without user sign-off)

### [FEATURE] `_ttm` annualisation for `frontend/fundamentals_service.py`
Same fix as the `repo/` version above but applied to the Streamlit frontend.
Grouped separately because `frontend/` is not production-critical.

### [METHODOLOGY] Revenue growth ≠ FCF growth in `frontend/dcf_model.py`
The 5-year Streamlit DCF model uses revenue CAGR as the FCF growth rate directly.
`repo/`'s 10-year model uses the FCF margin method which is more accurate. Aligning
`frontend/` to use a margin method would change DCF output values — requires approval.

---

## Completed

| Date | Item | Commit |
|------|------|--------|
| Nov 2026 | Phase 1 DCF safeguards applied to `repo/services/` (negative FCF, equity guard, blend filter, cross-val) | c9b9551 |
| Nov 2026 | Phase 1 DCF safeguards applied to `frontend/services/` (same fixes) | (prior session) |
| Nov 2026 | 42 production tests: `repo/services/tests/test_dcf_safeguards.py` | c9b9551 |
| Nov 2026 | 43 frontend tests: `frontend/services/tests/test_dcf_safeguards.py` | (prior session) |
| Nov 2026 | CLAUDE.md + `.claude/settings.json` autonomous permissions configured | c0c9ab2 |

---

## Opportunities (not yet assessed for approval)

*Add items here when identified during development cycles. Each entry needs: description,
why it would help, estimated complexity, and whether it requires approval.*

---

## Cycle log

| Date | Summary |
|------|---------|
| Nov 2026 | Phase 1.1 audit completed. Phase 1 production fixes committed. Autonomous dev permissions configured. Backlog initialised. |
