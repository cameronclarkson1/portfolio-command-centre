"""
coverage_audit.py — Full-universe valuation model coverage audit.

For each sector bucket, runs a representative sample of tickers through
run_valuation(), classifies every model N/A as CORRECT or BROKEN, and
produces a coverage-by-sector table plus a root-cause tally.

Run: python -m backtest.coverage_audit
"""

import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'repo'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'repo', '.env'))

import yfinance as yf
from services.valuation_engine import run_valuation
from backtest.sector_model_config import SECTOR_MODEL_CONFIG, BUCKET_SAMPLE_UNIVERSE

# ── Classification helpers ──────────────────────────────────────────────────

# Warning text substrings that mean "model correctly skipped" (expected N/A).
CORRECT_NA_SIGNALS = [
    "negative",
    "not appropriate",
    "early-stage",
    "insufficient",
    "no dividend",
    "dividend yield is zero",
    "not a reit",
    "affo per share is negative",       # negative after capex: correct if cap-heavy
]

# Warning text substrings that mean "model broken" (data missing, provider fail).
BROKEN_SIGNALS = [
    "missing",
    "unavailable",
    "cannot run",
    "share count missing",
    "no statements",
    "failed",
    "error",
    "net income or share count missing",
]

# Root-cause buckets (evaluated in order; first match wins).
ROOT_CAUSE_PATTERNS: list[tuple[str, str]] = [
    ("net income or share count missing", "RC1: FMP income-stmt 403 -> yfinance field mismatch (net_income/shares_outstanding)"),
    ("share count missing",               "RC1: FMP income-stmt 403 -> yfinance field mismatch (net_income/shares_outstanding)"),
    ("cannot run",                        "RC2: Required input computed as zero or None"),
    ("no statements",                     "RC3: Both FMP and yfinance statement fetch failed"),
    ("missing",                           "RC4: Specific field absent in returned statements"),
    ("unavailable",                       "RC3: Both FMP and yfinance statement fetch failed"),
    ("failed",                            "RC3: Both FMP and yfinance statement fetch failed"),
]


def classify_na(model_key: str, model_result: dict, bucket: str) -> tuple[str, str]:
    """
    Returns (classification, reason_code) where classification is:
      CORRECT  — model legitimately should not run for this ticker/bucket
      BROKEN   — model should run but data is missing/provider failed
      OK       — model produced a fair_value (not N/A)
    """
    if model_result.get("fair_value") is not None:
        return "OK", ""

    excluded = SECTOR_MODEL_CONFIG.get(bucket, {}).get("excluded", set())
    if model_key in excluded:
        return "CORRECT", "excluded-for-bucket"

    warnings = model_result.get("warnings") or []
    warning_text = " ".join(warnings).lower()

    for sig in CORRECT_NA_SIGNALS:
        if sig in warning_text:
            return "CORRECT", f"correct-na:{sig}"

    for sig in BROKEN_SIGNALS:
        if sig in warning_text:
            for pattern, code in ROOT_CAUSE_PATTERNS:
                if pattern in warning_text:
                    return "BROKEN", code
            return "BROKEN", f"RC_UNKNOWN:{warning_text[:80]}"

    if not warnings:
        return "BROKEN", "RC_UNKNOWN: no warning text, model returned None silently"

    return "BROKEN", f"RC_UNKNOWN:{warning_text[:80]}"


def run_ticker_audit(ticker: str, name: str, bucket: str) -> dict:
    """Run valuation for one ticker and classify all model outputs."""
    try:
        price_info = yf.Ticker(ticker).fast_info
        price = getattr(price_info, "last_price", None)
        if not price:
            hist = yf.download(ticker, period="2d", progress=False, auto_adjust=True)
            price = float(hist["Close"].iloc[-1]) if not hist.empty else None
        if not price:
            return {"ticker": ticker, "name": name, "bucket": bucket,
                    "error": "no price", "models": {}}

        price = round(float(price), 4)
        result = run_valuation(ticker, price)
        models_run = result.get("models_run", {})

        model_audit = {}
        config = SECTOR_MODEL_CONFIG.get(bucket, SECTOR_MODEL_CONFIG["default"])
        all_expected = config["primary"] | config["secondary"]

        # Classify all models that actually ran
        for mk, mv in models_run.items():
            classification, reason = classify_na(mk, mv, bucket)
            model_audit[mk] = {
                "fair_value":      mv.get("fair_value"),
                "classification":  classification,
                "reason_code":     reason,
                "warnings":        mv.get("warnings") or [],
            }

        # Flag primary models that didn't run at all (completely absent)
        for mk in config["primary"]:
            if mk not in model_audit:
                model_audit[mk] = {
                    "fair_value":     None,
                    "classification": "BROKEN",
                    "reason_code":    "RC5: model not dispatched — missing from models_run entirely",
                    "warnings":       [],
                }

        return {
            "ticker":        ticker,
            "name":          name,
            "bucket":        bucket,
            "price":         price,
            "fair_value_base": result.get("fair_value_base"),
            "rating":        result.get("valuation_rating"),
            "confidence":    result.get("overall_confidence"),
            "models":        model_audit,
        }

    except Exception as e:
        return {"ticker": ticker, "name": name, "bucket": bucket,
                "error": str(e), "models": {}}


def compute_coverage(ticker_results: list[dict], bucket: str) -> dict:
    """Compute primary-model coverage % for a bucket from ticker results."""
    config = SECTOR_MODEL_CONFIG.get(bucket, SECTOR_MODEL_CONFIG["default"])
    primary_models = config["primary"]

    if not primary_models:
        return {"primary_coverage_pct": 100.0, "model_detail": {}}

    model_ok_counts = {m: 0 for m in primary_models}
    ticker_count = 0

    for tr in ticker_results:
        if tr.get("error"):
            continue
        ticker_count += 1
        for m in primary_models:
            if tr["models"].get(m, {}).get("classification") == "OK":
                model_ok_counts[m] += 1

    if ticker_count == 0:
        return {"primary_coverage_pct": 0.0, "model_detail": {}}

    model_pcts = {m: round(c / ticker_count * 100, 1) for m, c in model_ok_counts.items()}
    avg_pct = round(sum(model_pcts.values()) / len(model_pcts), 1)
    return {"primary_coverage_pct": avg_pct, "model_detail": model_pcts}


def tally_root_causes(all_results: list[dict]) -> dict[str, list[str]]:
    """
    Tally BROKEN classifications by root-cause code.
    Returns {root_cause: [list of "TICKER.model" strings]}.
    """
    tally: dict[str, list[str]] = {}
    for tr in all_results:
        for mk, mv in tr.get("models", {}).items():
            if mv["classification"] == "BROKEN":
                rc = mv["reason_code"]
                tally.setdefault(rc, []).append(f"{tr['ticker']}.{mk}")
    return tally


def run():
    print("=" * 72)
    print("COVERAGE AUDIT — Full-universe valuation model coverage by sector")
    print("=" * 72)

    all_ticker_results: list[dict] = []
    bucket_results: dict[str, list[dict]] = {}

    total_tickers = sum(len(v) for v in BUCKET_SAMPLE_UNIVERSE.values())
    done = 0

    for bucket, tickers in BUCKET_SAMPLE_UNIVERSE.items():
        print(f"\n--- {bucket.upper()} ---")
        bucket_list = []
        for ticker, name in tickers:
            done += 1
            print(f"  [{done:>2}/{total_tickers}] {ticker:<8} {name}", end="  ", flush=True)
            tr = run_ticker_audit(ticker, name, bucket)
            bucket_list.append(tr)
            all_ticker_results.append(tr)

            if tr.get("error"):
                print(f"ERROR: {tr['error']}")
            else:
                ok_count   = sum(1 for mv in tr["models"].values() if mv["classification"] == "OK")
                broken     = [mk for mk, mv in tr["models"].items() if mv["classification"] == "BROKEN"]
                correct_na = [mk for mk, mv in tr["models"].items() if mv["classification"] == "CORRECT"]
                print(f"OK={ok_count}  broken={broken or '-'}  correct_na={correct_na or '-'}")

            time.sleep(0.3)  # avoid hammering yfinance

        bucket_results[bucket] = bucket_list

    # ── Coverage-by-sector table ────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("COVERAGE BY SECTOR (sorted worst-first)")
    print("=" * 72)

    coverage_rows = []
    for bucket, results in bucket_results.items():
        cov = compute_coverage(results, bucket)
        coverage_rows.append((bucket, cov["primary_coverage_pct"], cov["model_detail"], results))

    coverage_rows.sort(key=lambda r: r[1])  # ascending = worst first

    print(f"\n  {'Bucket':<22} {'Coverage':>9}   {'Model detail'}")
    print(f"  {'-'*22} {'-'*9}   {'-'*40}")
    for bucket, pct, detail, _ in coverage_rows:
        ok_sym = "OK" if pct >= 80 else ("WARN" if pct >= 50 else "FAIL")
        detail_str = "  ".join(f"{m}={v:.0f}%" for m, v in sorted(detail.items()))
        print(f"  [{ok_sym:<4}] {bucket:<22} {pct:>6.1f}%   {detail_str}")

    # ── Root-cause tally ────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("ROOT-CAUSE TALLY (BROKEN model occurrences)")
    print("=" * 72)

    tally = tally_root_causes(all_ticker_results)
    if not tally:
        print("\n  No BROKEN models detected.")
    else:
        for rc, instances in sorted(tally.items(), key=lambda x: -len(x[1])):
            print(f"\n  [{len(instances):>2}x] {rc}")
            for inst in instances:
                print(f"         {inst}")

    # ── Per-ticker detail ───────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("PER-TICKER MODEL DETAIL")
    print("=" * 72)

    for bucket, _, _, results in coverage_rows:
        config  = SECTOR_MODEL_CONFIG.get(bucket, SECTOR_MODEL_CONFIG["default"])
        primary = config["primary"]
        print(f"\n  {bucket.upper()}   (primary: {', '.join(sorted(primary))})")
        for tr in results:
            if tr.get("error"):
                print(f"    {tr['ticker']:<8} ERROR: {tr['error']}")
                continue
            parts = []
            for mk in sorted(tr["models"].keys()):
                mv = tr["models"][mk]
                tag = "OK" if mv["classification"] == "OK" else ("--" if mv["classification"] == "CORRECT" else "XX")
                parts.append(f"{mk}:{tag}")
            print(f"    {tr['ticker']:<8} {tr.get('rating','?'):<20} {' '.join(parts)}")

    # ── Fix priority list ────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("RANKED FIX LIST (by number of affected instances)")
    print("=" * 72)

    if tally:
        rank = sorted(tally.items(), key=lambda x: -len(x[1]))
        for i, (rc, instances) in enumerate(rank, 1):
            unique_models  = set(inst.split(".")[1] for inst in instances)
            unique_tickers = set(inst.split(".")[0] for inst in instances)
            print(f"\n  #{i}  {rc}")
            print(f"      Affects {len(instances)} model-run(s): models={sorted(unique_models)}  tickers={sorted(unique_tickers)}")
    else:
        print("\n  Nothing to fix — all primary models covering > 0 tickers.")

    # ── Sectors to exclude from backtest ───────────────────────────────────
    print("\n" + "=" * 72)
    print("BACKTEST EXCLUSION LIST (primary coverage < 66%)")
    print("=" * 72)

    exclusions = [(b, p) for b, p, _, _ in coverage_rows if p < 66.0]
    if exclusions:
        for b, p in exclusions:
            print(f"  EXCLUDE {b:<22} coverage={p:.1f}%")
    else:
        print("  No sectors below threshold — all sectors eligible for backtest.")

    # ── Save ────────────────────────────────────────────────────────────────
    out_path = os.path.join(os.path.dirname(__file__), "coverage_audit_results.json")
    save_data = {
        "coverage": [
            {"bucket": b, "primary_coverage_pct": p, "model_detail": d}
            for b, p, d, _ in coverage_rows
        ],
        "root_causes": {rc: instances for rc, instances in tally.items()},
        "ticker_results": [
            {k: v for k, v in tr.items() if k != "models"}
            | {"models": {mk: {kk: vv for kk, vv in mv.items() if kk != "warnings"}
                          for mk, mv in tr.get("models", {}).items()}}
            for tr in all_ticker_results
        ],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\nFull results saved to: {out_path}")
    print("=" * 72)


if __name__ == "__main__":
    run()
