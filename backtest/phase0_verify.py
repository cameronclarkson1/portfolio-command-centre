"""
Phase 0.1 - Engine verification for AAPL, MSFT, VICI.
Checks: upside formula, no impossible margins, no Insufficient-data on large-caps,
multiples are not static constants (varies by ticker).

Run: python -m backtest.phase0_verify
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'repo'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'repo', '.env'))

from services.valuation_engine import run_valuation
from services.scoring_service  import compute_scores
from services.fundamentals_service import get_financial_statements, get_key_ratios

TICKERS = ["AAPL", "MSFT", "VICI"]

def check_upside(result):
    fvb   = result.get("fair_value_base")
    price = result.get("_price")
    up    = result.get("upside_pct")
    if fvb is None or price is None or up is None:
        return False, "missing fair_value_base / upside_pct"
    expected = (fvb - price) / price
    if abs(expected - up) > 0.0001:
        return False, f"upside mismatch: got {up:.4f}, expected {expected:.4f}"
    return True, f"upside OK ({up*100:+.1f}%)"

def check_margins(result, ticker):
    price    = result.get("_price", 1)
    models   = result.get("models_run", {})
    problems = []
    for k, v in models.items():
        fv = v.get("fair_value")
        if fv is None:
            continue
        if fv <= 0:
            problems.append(f"{k}: fv={fv}")
        if fv > price * 50:
            problems.append(f"{k}: fv={fv:.0f} > 50x price")
    if problems:
        return False, "Impossible fair values: " + ", ".join(problems)
    return True, f"{len(models)} models all within bounds"

def check_data_sufficient(result):
    conf   = result.get("overall_confidence", 0)
    models = {k: v for k, v in result.get("models_run", {}).items()
              if v.get("fair_value") is not None}
    if len(models) < 2:
        return False, f"Only {len(models)} models returned fair_value"
    if conf < 40:
        return False, f"Confidence too low: {conf}%"
    return True, f"{len(models)} models, confidence={conf}%"

def check_multiples_vary(results):
    pe_fvs = {}
    for ticker, res in results.items():
        m = res.get("models_run", {})
        if "pe" in m and m["pe"].get("fair_value"):
            pe_fvs[ticker] = round(m["pe"]["fair_value"], 2)
    if len(pe_fvs) < 2:
        return None, "Not enough tickers have P/E models to compare"
    vals = list(pe_fvs.values())
    if all(abs(v - vals[0]) < 1.0 for v in vals):
        return False, f"P/E fair values suspiciously uniform: {pe_fvs}"
    return True, f"P/E fair values differ across tickers: {pe_fvs}"

def run():
    print("=" * 70)
    print("PHASE 0.1 - VALUATION ENGINE VERIFICATION")
    print("=" * 70)

    import yfinance as yf

    all_results = {}
    failures    = []

    for ticker in TICKERS:
        print(f"\n--- {ticker} ---")
        try:
            price = yf.Ticker(ticker).fast_info.get("lastPrice")
            if not price:
                hist  = yf.download(ticker, period="2d", progress=False)
                price = float(hist["Close"].iloc[-1])
            price = round(float(price), 4)
            print(f"  Live price: ${price:.2f}")

            result = run_valuation(ticker, price)
            result["_price"] = price
            all_results[ticker] = result

            ok, msg = check_upside(result)
            print(f"  [{'PASS' if ok else 'FAIL'}] Upside formula: {msg}")
            if not ok: failures.append(f"{ticker} upside: {msg}")

            ok, msg = check_margins(result, ticker)
            print(f"  [{'PASS' if ok else 'FAIL'}] Margin bounds:  {msg}")
            if not ok: failures.append(f"{ticker} margins: {msg}")

            ok, msg = check_data_sufficient(result)
            print(f"  [{'PASS' if ok else 'FAIL'}] Data quality:   {msg}")
            if not ok: failures.append(f"{ticker} data: {msg}")

            print(f"  Models:")
            for mk, mv in result.get("models_run", {}).items():
                fv   = mv.get("fair_value")
                conf = mv.get("confidence", 0)
                fv_s = f"${fv:.2f}" if fv else "N/A"
                print(f"    {mk:<14} fv={fv_s:<12} conf={conf:.0f}%")

            fvb = result.get("fair_value_base")
            fvl = result.get("fair_value_low")
            fvh = result.get("fair_value_high")
            up  = result.get("upside_pct", 0)
            rat = result.get("valuation_rating", "?")
            print(f"  Blended: ${fvl:.2f} / ${fvb:.2f} / ${fvh:.2f}  upside={up*100:+.1f}%  rating={rat}")

        except Exception as e:
            import traceback
            print(f"  [FAIL] EXCEPTION: {e}")
            traceback.print_exc()
            failures.append(f"{ticker}: exception - {e}")

    print(f"\n--- Cross-ticker check ---")
    ok, msg = check_multiples_vary(all_results)
    if ok is None:
        print(f"  [SKIP] Multiples vary: {msg}")
    else:
        print(f"  [{'PASS' if ok else 'FAIL'}] Multiples vary: {msg}")
        if not ok: failures.append(f"multiples: {msg}")

    print("\n" + "=" * 70)
    if failures:
        print("PHASE 0.1 RESULT: FAILED - fixes not verified")
        for f in failures:
            print(f"  FAIL: {f}")
        print("\nDo NOT proceed to backtest until these are resolved.")
    else:
        print("PHASE 0.1 RESULT: PASSED - engine checks out")
        print("Proceed to Phase 0.2 data-availability audit.")
    print("=" * 70)

    out_path = os.path.join(os.path.dirname(__file__), "phase0_verify_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        clean = {t: {k: v for k, v in r.items() if k != "_price"}
                 for t, r in all_results.items()}
        json.dump(clean, f, indent=2, default=str)
    print(f"\nRaw results saved to: {out_path}")

if __name__ == "__main__":
    run()
