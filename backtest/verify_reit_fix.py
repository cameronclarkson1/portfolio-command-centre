"""
verify_reit_fix.py — Numeric verification for the P/FFO / P/AFFO fix.

Runs VICI and O end-to-end after the share-count fallback-chain fix and reports:
  - P/FFO and P/AFFO fair values and which source supplied the share count
  - How the blended fair value and rating changed vs. the pre-fix result
  - Whether the values are sensible for each REIT

Run: python -m backtest.verify_reit_fix
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'repo'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'repo', '.env'))

import yfinance as yf
from services.valuation_engine import run_valuation

# Pre-fix blended fair values from Phase 0.1 / coverage audit (for comparison)
PRE_FIX = {
    "VICI": {"fair_value_base": 40.67, "rating": "Undervalued", "primary_models": "pb+ddm+pcf"},
    "O":    {"fair_value_base": None,   "rating": "Slightly Undervalued", "primary_models": "pb+ddm+pcf"},
}

# Sanity ranges: P/FFO fair value for each REIT based on public analyst estimates
SANITY = {
    "VICI": {"pffo_lo": 20, "pffo_hi": 50},   # gaming REIT; ~$26 stock
    "O":    {"pffo_lo": 40, "pffo_hi": 75},   # net-lease; ~$58 stock
}

TICKERS = [
    ("VICI", "VICI Properties — gaming REIT"),
    ("O",    "Realty Income   — net-lease REIT"),
]

def run():
    print("=" * 72)
    print("REIT FIX VERIFICATION — P/FFO + P/AFFO post share-count fix")
    print("=" * 72)

    for ticker, label in TICKERS:
        print(f"\n{'='*72}")
        print(f"  {label}")
        print("=" * 72)

        price_info = yf.Ticker(ticker).fast_info
        price = round(float(getattr(price_info, "last_price", None) or 0), 2)
        print(f"\n  Live price: ${price:.2f}")

        result = run_valuation(ticker, price)
        models = result.get("models_run", {})

        # ── P/FFO ─────────────────────────────────────────────────────────────
        pffo = models.get("pffo", {})
        pffo_fv  = pffo.get("fair_value")
        pffo_src = (pffo.get("inputs_used") or {}).get("shares_source", "N/A")
        pffo_fpo = (pffo.get("inputs_used") or {}).get("ffo_per_share")
        pffo_conf = pffo.get("confidence", 0)
        pffo_warn = pffo.get("warnings", [])

        print(f"\n  P/FFO:")
        if pffo_fv is not None:
            sane = SANITY[ticker]["pffo_lo"] <= pffo_fv <= SANITY[ticker]["pffo_hi"]
            sanity_tag = "SANE" if sane else "CHECK"
            print(f"    fair_value   = ${pffo_fv:.2f}  [{sanity_tag}]")
            print(f"    FFO/share    = ${pffo_fpo:.2f}" if pffo_fpo else "    FFO/share    = N/A")
            print(f"    shares_source = {pffo_src}")
            print(f"    confidence   = {pffo_conf:.0f}%")
        else:
            print(f"    fair_value = N/A")
            for w in pffo_warn:
                print(f"    WARNING: {w}")

        # ── P/AFFO ────────────────────────────────────────────────────────────
        paffo = models.get("paffo", {})
        paffo_fv  = paffo.get("fair_value")
        paffo_src = (paffo.get("inputs_used") or {}).get("shares_source", "N/A")
        paffo_afps = (paffo.get("inputs_used") or {}).get("affo_per_share")
        paffo_conf = paffo.get("confidence", 0)
        paffo_warn = paffo.get("warnings", [])

        print(f"\n  P/AFFO:")
        if paffo_fv is not None:
            print(f"    fair_value   = ${paffo_fv:.2f}")
            print(f"    AFFO/share   = ${paffo_afps:.2f}" if paffo_afps else "    AFFO/share   = N/A")
            print(f"    shares_source = {paffo_src}")
            print(f"    confidence   = {paffo_conf:.0f}%")
        else:
            print(f"    fair_value = N/A")
            for w in paffo_warn:
                print(f"    WARNING: {w}")

        # ── Blended result ────────────────────────────────────────────────────
        fvb = result.get("fair_value_base")
        fvl = result.get("fair_value_low")
        fvh = result.get("fair_value_high")
        rating = result.get("valuation_rating", "?")
        upside = result.get("upside_pct", 0)
        conf   = result.get("overall_confidence", 0)

        pre = PRE_FIX.get(ticker, {})
        pre_fvb = pre.get("fair_value_base")
        pre_rating = pre.get("rating", "?")
        pre_models = pre.get("primary_models", "?")

        print(f"\n  BLENDED:")
        print(f"    range        = ${fvl:.2f} / ${fvb:.2f} / ${fvh:.2f}")
        print(f"    upside       = {upside*100:+.1f}%")
        print(f"    rating       = {rating}")
        print(f"    confidence   = {conf}%")
        print(f"\n  BEFORE FIX (pre-audit):")
        print(f"    fair_value   = ${pre_fvb:.2f}" if pre_fvb else "    fair_value   = unknown")
        print(f"    rating       = {pre_rating}")
        print(f"    primary models used = {pre_models}")

        if fvb and pre_fvb:
            delta = (fvb - pre_fvb) / pre_fvb
            print(f"\n  DELTA: fair value {delta*100:+.1f}% ({'+' if delta >= 0 else ''}{fvb - pre_fvb:.2f})")

        # ── All models run ─────────────────────────────────────────────────────
        print(f"\n  All models:")
        for mk, mv in models.items():
            fv   = mv.get("fair_value")
            conf = mv.get("confidence", 0)
            fv_s = f"${fv:.2f}" if fv else "N/A"
            print(f"    {mk:<14} fv={fv_s:<12} conf={conf:.0f}%")

    print("\n" + "=" * 72)
    print("DONE")
    print("=" * 72)

if __name__ == "__main__":
    run()
