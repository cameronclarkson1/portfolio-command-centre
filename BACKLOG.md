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
| Nov 2026 | Extracted shared `ttm_sum()` to `repo/utils/financial_calcs.py`; extended annualisation to `reit_valuation._annualise`, `relative_valuation._ttm_income/_ttm_cashflow` | b260cc6 |
| Nov 2026 | 23 new tests covering `_annualise`, `_ttm_income`, `_ttm_cashflow`, `run_pffo`, `run_pe` with 1–4 quarter inputs | 510ec0b |

---

## Cycle 4 Audit Findings — Ready for Implementation

Findings from the Cycle 4 full platform quality audit (read-only, Nov 2026).
Sorted by priority. Items marked [NEEDS APPROVAL] must not be implemented without explicit sign-off.

### CRITICAL — ✅ COMPLETED in Cycle 5

**C-1 · ND/EBITDA single-quarter EBITDA bug — FIXED (`97bdd40`)**  
Root cause: `ebitda_v = (incomes[0] or {}).get("ebitda")` used a single quarter value.
Fix: `ebitda_ttm = sum((_safe_float((r or {}).get("ebitda")) or 0.0) for r in incomes[:4])`
Before: true ND/EBITDA=1.5 computed as 6.0 → nd_score=5. After: ratio=1.5 → nd_score=80.
22 regression tests in `test_c1_nd_ebitda.py`. 130/130 tests pass.

**C-2 · REIT early-stage misclassification — FIXED (`377de04`)**  
Root cause: `is_early_stage()` called unconditionally; REITs with negative GAAP net income
(normal due to large property depreciation) were overridden to `early_stage` bucket.
Fix: guard in `valuation_engine.py` — skip override for `bucket in ("reit", "financials", "insurance")`.
30 regression tests in `test_c2_reit_classification.py`. 130/130 tests pass.

### HIGH — ✅ ALL COMPLETED in Cycle 6

**H-1 · `scoring_service._ttm` does not annualise — FIXED (`a70ab24`)**  
Local `_ttm()` in `build_scoring_inputs()` now annualises by n/n_actual for <4 quarters.
16 regression tests in `test_h1_scoring_ttm.py`.

**H-2 · Income series chart shows single quarterly values as annual — FIXED (`8f7f8a5`)**  
`_extract_income_series()` now aggregates quarterly records by calendar year (sums revenue).
11 regression tests in `test_h2_income_series.py`.

**H-3 · `fcf_per_share` uses raw sum in `get_key_ratios` — FIXED (`3b24738`)**  
`_fcf_ttm` now uses `ttm_sum(_cashflow, "free_cash_flow")`.
12 regression tests in `test_h3_fcf_per_share.py`.

**H-4 · FCF CAGR is 3-quarter window exponentiated as 3-year CAGR — FIXED (`7f6423f`)**  
Now compares TTM `cashflows[:4]` vs TTM `cashflows[8:12]`; requires 12+ quarters.
16 regression tests in `test_h4_fcf_cagr.py`.

### MEDIUM

**M-1 · DDM ERP is 5.5%; DCF uses Damodaran 4.6% (`ddm_model.py:76`)** [NEEDS APPROVAL]  
DDM `market_premium = 0.055` hardcoded vs `DAMODARAN_ERP = 0.046` in `data/damodaran_betas.py`.
DDM systematically undervalues vs DCF (affects Consumer Staples, Utilities, Financials buckets).
**Fix:** import `DAMODARAN_ERP` and use it. Requires approval — changes financial methodology constant.

**M-2 · Completeness score penalises zero fields — FIXED (`71a632b`)**  
Three locations now use `is not None` / `not in (None, "")` instead of `not in (None, 0)`.
13 regression tests in `test_m2_zero_valid_completeness.py`.

**M-3 · `select_models` raw sums — FIXED (`b3b210c`)**  
`eps_ttm` and `op_cf_ttm` now use `ttm_sum()`. Import added to sector_mapper.py.
9 regression tests in `test_m3_sector_mapper_ttm.py`.

**M-4 · EV model negative equity value not warned — FIXED (`eb73ba4`)**  
Both `run_ev_ebitda` and `run_ev_sales` now guard against negative equity after net_debt subtraction.
10 regression tests in `test_m4_negative_equity_guard.py`.

**M-5 · ROIC from annual FMP metrics only — up to 12 months stale (`fmp_provider.py:207`)**  
FMP stable plan returns annual key metrics only. ROIC/ROE used for quality-adjusted multiples
can be a full fiscal year old. **Fix:** compute TTM ROIC from quarterly statements already fetched. No approval needed.

### LOW — ✅ ALL COMPLETED in Cycle 6

**L-1 · `val_inputs` cache TTL is 24h — FIXED (`b5d07c4`)**  
Added `CACHE_TTL["val_inputs"] = 3600`; `get_valuation_inputs()` now references it.
4 regression tests in `test_l1_val_inputs_cache_ttl.py`.

**L-2 · `get_analyst_estimates` raises ValueError on empty response — FIXED (`affea2f`)**  
Now returns `[]` instead of raising. 4 regression tests in `test_l2_analyst_estimates_graceful.py`.

**L-3 · CORS policy allows all origins in production — FIXED (`d8db80b`)**  
`api/main.py` reads `CORS_ALLOW_ORIGIN` env var; falls back to `["*"]` when unset.
6 regression tests in `test_l3_cors_origins.py`.

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
| Nov 2026 | Cycle 3: Extended TTM annualisation to reit_valuation and relative_valuation via shared utils/financial_calcs.py. Added 23 tests. 78/78 tests pass. All commits pushed to origin/master. |
| Nov 2026 | Cycle 4: Full read-only audit. Identified 2 critical bugs (ND/EBITDA single-quarter EBITDA; REIT early-stage misclassification), 4 high, 5 medium, 3 low findings. BACKLOG updated. No application code changed. |
| Nov 2026 | Deployment: Vercel account upgraded Hobby → Pro. Resolved hourly cron rejection (`0 * * * *` in `nextjs-frontend/vercel.json` for `/api/keepalive`). Fixed `next-env.d.ts` dev→production types path. Pushed 8ee1c0e to trigger redeploy. |
| Nov 2026 | Cycle 5: Fixed C-1 (ND/EBITDA single-quarter EBITDA, scoring_service.py, 97bdd40) and C-2 (REIT early-stage misclassification, valuation_engine.py, 377de04). 52 new regression tests added. 130/130 tests pass. Pushed to origin/master. |
| Nov 2026 | Cycle 6: Fixed all 10 audit findings (H-1 through L-3). Key fixes: TTM annualisation in scoring/fundamentals (H-1, H-3), FCF CAGR 12-quarter window (H-4), quarterly revenue aggregation (H-2), negative equity guard in EV models (M-4), zero-as-valid in completeness checks (M-2), ttm_sum in select_models (M-3), val_inputs TTL 1h (L-1), graceful empty estimates (L-2), CORS from env var (L-3). 101 new regression tests added. 231/231 tests pass. |
