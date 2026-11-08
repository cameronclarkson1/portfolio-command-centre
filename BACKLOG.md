# Development Backlog — Portfolio Command Centre

This file is the persistent task list for autonomous development cycles.
Read it at the start of every cycle. Update it as tasks are started, completed, or discovered.

---

## In Progress

*(nothing currently in progress — start here)*

---

## Ready (approved, unblocked)

*(all tasks completed in Cycle 2 — backlog is clear)*

---

## Needs Approval (do not implement without user sign-off)

### [FEATURE] `_ttm` annualisation for `frontend/fundamentals_service.py`
~~Same fix as the `repo/` version above but applied to the Streamlit frontend.~~  
**N/A — `frontend/` directory is not present in this repository (gitignored).**

### [METHODOLOGY] Revenue growth ≠ FCF growth in `frontend/dcf_model.py`
~~The 5-year Streamlit DCF model uses revenue CAGR as the FCF growth rate directly.~~  
**N/A — `frontend/` directory is not present in this repository (gitignored).**

---

## Completed

| Date | Item | Commit |
|------|------|--------|
| Nov 2026 | Phase 1 DCF safeguards applied to `repo/services/` (negative FCF, equity guard, blend filter, cross-val) | c9b9551 |
| Nov 2026 | Phase 1 DCF safeguards applied to `frontend/services/` (same fixes) | (prior session) |
| Nov 2026 | 42 production tests: `repo/services/tests/test_dcf_safeguards.py` | c9b9551 |
| Nov 2026 | 43 frontend tests: `frontend/services/tests/test_dcf_safeguards.py` | (prior session) |
| Nov 2026 | CLAUDE.md + `.claude/settings.json` autonomous permissions configured | c0c9ab2 |
| Nov 2026 | Fixed `_ttm` annualisation bias in `repo/services/fundamentals_service.py` + 13 unit tests | b683a4b |
| Nov 2026 | Deleted `run_dcf_model` and `_save_valuation_to_db` dead code from `repo/services/valuation_service.py` | 704cd90 |

---

## Opportunities (not yet assessed for approval)

*Add items here when identified during development cycles. Each entry needs: description,
why it would help, estimated complexity, and whether it requires approval.*

---

## Cycle log

| Date | Summary |
|------|---------|
| Nov 2026 | Phase 1.1 audit completed. Phase 1 production fixes committed. Autonomous dev permissions configured. Backlog initialised. |
| Nov 2026 | Cycle 2: Cleared all 3 Ready tasks. Fixed `_ttm` annualisation (b683a4b). Removed dead code (704cd90). Marked frontend/ tasks N/A — directory not in repo. 55/55 tests pass. |
