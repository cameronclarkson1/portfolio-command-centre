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

### CRITICAL — implement first

**C-1 · ND/EBITDA single-quarter EBITDA bug (`scoring_service.py:534`)**  
`ebitda_v = (incomes[0] or {}).get("ebitda")` is a single quarter value. Dividing balance-sheet
net debt by one quarter of EBITDA inflates the ND/EBITDA ratio ~4× for every company.
Score impact: a company with correct ND/EBITDA=2× shows as 8×, scoring 18/100 instead of ~80/100.
Affects all stocks with any debt. **Fix:** sum `incomes[:4]` for `ebitda_ttm` before dividing.
No approval needed — pure bug fix.

**C-2 · REIT early-stage misclassification (`sector_mapper.py:251`)**  
`is_early_stage()` checks raw GAAP `net_income_ttm`. REITs with negative GAAP net income
(common from large depreciation charges) trigger early-stage override, replacing P/FFO/P/AFFO
with EV/Sales/P/CF — entirely wrong models. The correct valuation is silently discarded.
**Fix:** add a bucket guard (`if bucket in ("reit", "financials", "insurance"): return False`).
No approval needed — bug fix restoring the intended sector-model assignment.

### HIGH

**H-1 · `scoring_service._ttm` does not annualise (`scoring_service.py:478`)**  
Local `_ttm()` function in `build_scoring_inputs()` is not the shared `ttm_sum`.
FCF and net income used for quality/safety scoring are understated for companies with <4 quarters.
**Fix:** import and use `ttm_sum` from `utils.financial_calcs`. No approval needed.

**H-2 · Income series chart shows single quarterly values as annual (`research.py:30`)**  
`_extract_income_series()` deduplicates quarterly data by year, keeping the first (most recent)
quarter — labels Q3 revenue as the full "2024" year. Display-only bug; valuation models unaffected.
**Fix:** aggregate quarterly rows by year (sum revenue, last EPS). No approval needed.

**H-3 · `fcf_per_share` uses raw sum in `get_key_ratios` (`fundamentals_service.py:199`)**  
`_fcf_ttm = sum(q.get("free_cash_flow") or 0 for q in _cashflow[:4])` — raw sum not annualised.
Feeds P/CF fallback; understates FCF/share by up to 50% for <4 quarter companies.
**Fix:** replace with `_ttm(_cashflow, "free_cash_flow")` using the existing module alias. No approval needed.

**H-4 · FCF CAGR is 3-quarter window exponentiated as 3-year CAGR (`scoring_service.py:507`)**  
`cashflows[0]` vs `cashflows[3]` is 3 quarters of history, not 3 years.
`** (1.0/3.0)` treats it as a 3-year CAGR — systematically wrong growth score.
**Fix:** compare TTM of `cashflows[:4]` vs TTM of `cashflows[8:12]` (true 3-year window); skip if <12 quarters available. No approval needed.

### MEDIUM

**M-1 · DDM ERP is 5.5%; DCF uses Damodaran 4.6% (`ddm_model.py:76`)** [NEEDS APPROVAL]  
DDM `market_premium = 0.055` hardcoded vs `DAMODARAN_ERP = 0.046` in `data/damodaran_betas.py`.
DDM systematically undervalues vs DCF (affects Consumer Staples, Utilities, Financials buckets).
**Fix:** import `DAMODARAN_ERP` and use it. Requires approval — changes financial methodology constant.

**M-2 · Completeness score penalises zero fields (`fundamentals_service.py:554`)**  
`inputs.get(k) not in (None, 0)` treats zero net debt as missing data.
Debt-free companies receive a lower confidence score. **Fix:** use `is None` check for numerics. No approval needed.

**M-3 · `select_models` / `is_early_stage` raw sums (`sector_mapper.py:197`)**  
`eps_ttm`, `op_cf_ttm`, `net_income_ttm` all use raw sums without annualisation.
May incorrectly exclude P/E or P/CF as eligible models for <4 quarter companies.
**Fix:** use `ttm_sum`. No approval needed.

**M-4 · EV model negative equity value not warned (`relative_valuation.py:343`)**  
When `net_debt > implied_ev`, `fair_value` is negative and silently dropped by the blend filter.
No explanatory warning is returned. **Fix:** explicit guard with meaningful warning string. No approval needed.

**M-5 · ROIC from annual FMP metrics only — up to 12 months stale (`fmp_provider.py:207`)**  
FMP stable plan returns annual key metrics only. ROIC/ROE used for quality-adjusted multiples
can be a full fiscal year old. **Fix:** compute TTM ROIC from quarterly statements already fetched. No approval needed.

### LOW

**L-1 · `val_inputs` cache TTL is 24h; valuation cache is 1h (`settings.py:26`)**  
After earnings, valuation reruns in 1h but pulls 24h-old fundamentals. Post-earnings repricing
is delayed. **Fix:** align `val_inputs` TTL to 1h, or bust both caches together. No approval needed.

**L-2 · `get_analyst_estimates` raises ValueError on empty response (`fmp_provider.py:397`)**  
Small-caps/ETFs with no coverage trigger a ValueError that is swallowed by the caller,
producing log noise. **Fix:** return `[]` on empty, consistent with other endpoints. No approval needed.

**L-3 · CORS policy allows all origins in production (`api/main.py:88`)**  
`allow_origins=["*"]` exposes the portfolio API to any browser origin.
**Fix:** restrict to Vercel production domain + localhost:3000 via environment variable. No approval needed.

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
