"""
forward_returns.py — Fetch forward price returns for a completed snapshot.

Reads a Day-0 snapshot file and adds the actual price return over a given
horizon. Run this at T+1M, T+3M, T+6M, and T+12M after the original snapshot.

Usage:
  python -m backtest.forward_returns --snapshot 2026-07-18 --horizon 1m
  python -m backtest.forward_returns --snapshot 2026-07-18 --horizon 3m
  python -m backtest.forward_returns --snapshot 2026-07-18 --horizon 6m
  python -m backtest.forward_returns --snapshot 2026-07-18 --horizon 12m

Output:
  backtest/snapshots/returns_2026-07-18_1m.csv   — ticker, rating, return, sector
  backtest/snapshots/results_2026-07-18_1m.json  — analysis: mean return by rating bucket

Survivorship-bias note: tickers that were delisted / acquired between Day-0 and
the horizon date will show as missing in yfinance. These are excluded from the
analysis and logged separately. This is a KNOWN UPWARD BIAS — the script reports
the count of excluded tickers so the reader can judge materiality.
"""

import sys, os, json, csv, argparse
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'repo'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'repo', '.env'))

import yfinance as yf

SNAPSHOT_DIR  = Path(__file__).parent / "snapshots"
HORIZON_DAYS  = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}

RETURN_FIELDS = [
    "ticker", "snapshot_date", "horizon",
    "price_day0", "price_horizon", "total_return",
    "rating", "upside_pct_day0", "fair_value_base_day0",
    "sector", "bucket", "models_ok",
]


def load_snapshot(snapshot_date: str) -> list[dict]:
    jsonl_path = SNAPSHOT_DIR / f"snapshot_{snapshot_date}.jsonl"
    if not jsonl_path.exists():
        raise FileNotFoundError(f"No snapshot found: {jsonl_path}")
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get("price") and r.get("rating") and not r.get("error"):
                    records.append(r)
            except json.JSONDecodeError:
                pass
    return records


def fetch_price_at_horizon(ticker: str, snapshot_date: str, trading_days: int) -> float | None:
    """
    Fetch the closing price approximately `trading_days` after the snapshot.
    Uses yfinance history — returns None if the ticker has no data (delisted, etc.).
    """
    try:
        start = date.fromisoformat(snapshot_date)
        # Add buffer: request extra calendar days to account for weekends/holidays
        end_date = start + timedelta(days=trading_days * 2)
        hist = yf.download(
            ticker,
            start=(start + timedelta(days=1)).isoformat(),
            end=end_date.isoformat(),
            progress=False,
            auto_adjust=True,
        )
        if hist.empty:
            return None
        # Take the row closest to our target trading-day count
        if len(hist) >= trading_days:
            return round(float(hist["Close"].iloc[trading_days - 1]), 4)
        else:
            return round(float(hist["Close"].iloc[-1]), 4)   # best available
    except Exception:
        return None


def run(snapshot_date: str, horizon: str) -> None:
    trading_days = HORIZON_DAYS.get(horizon)
    if not trading_days:
        raise ValueError(f"Unknown horizon '{horizon}'. Use: {list(HORIZON_DAYS)}")

    records = load_snapshot(snapshot_date)
    out_csv  = SNAPSHOT_DIR / f"returns_{snapshot_date}_{horizon}.csv"
    out_json = SNAPSHOT_DIR / f"results_{snapshot_date}_{horizon}.json"

    print("=" * 70)
    print(f"FORWARD RETURNS — snapshot={snapshot_date}  horizon={horizon} (~{trading_days} trading days)")
    print(f"  {len(records)} tickers to price")
    print("=" * 70)

    return_rows  = []
    missing      = []

    for i, rec in enumerate(records, 1):
        ticker = rec["ticker"]
        p0     = rec["price"]
        print(f"  [{i:>3}/{len(records)}]  {ticker:<8}", end="  ", flush=True)

        ph = fetch_price_at_horizon(ticker, snapshot_date, trading_days)

        if ph is None:
            print("NO DATA (delisted/unavailable)")
            missing.append(ticker)
            continue

        total_return = (ph - p0) / p0
        row = {
            "ticker":             ticker,
            "snapshot_date":      snapshot_date,
            "horizon":            horizon,
            "price_day0":         p0,
            "price_horizon":      ph,
            "total_return":       round(total_return, 6),
            "rating":             rec.get("rating", ""),
            "upside_pct_day0":    rec.get("upside_pct"),
            "fair_value_base_day0": rec.get("fair_value_base"),
            "sector":             rec.get("sector", ""),
            "bucket":             rec.get("bucket", ""),
            "models_ok":          rec.get("models_ok", ""),
        }
        return_rows.append(row)
        print(f"${p0:.2f} → ${ph:.2f}  return={total_return*100:+.1f}%  [{rec.get('rating','')}]")

    # Write CSV
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RETURN_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(return_rows)

    # Analyse by rating bucket
    rating_order = [
        "Undervalued", "Slightly Undervalued", "Fairly Valued",
        "Slightly Overvalued", "Overvalued",
    ]
    analysis: dict[str, dict] = {}
    for rating in rating_order:
        group = [r["total_return"] for r in return_rows if r["rating"] == rating]
        if not group:
            continue
        analysis[rating] = {
            "count":        len(group),
            "mean_return":  round(sum(group) / len(group), 6),
            "median_return": round(sorted(group)[len(group) // 2], 6),
            "positive_pct": round(sum(1 for r in group if r > 0) / len(group), 4),
        }

    # Sector breakdown
    by_bucket: dict[str, list] = {}
    for r in return_rows:
        by_bucket.setdefault(r["bucket"], []).append(r["total_return"])
    bucket_analysis = {
        b: {
            "count": len(rets),
            "mean_return": round(sum(rets) / len(rets), 6),
        }
        for b, rets in by_bucket.items()
    }

    results = {
        "snapshot_date":    snapshot_date,
        "horizon":          horizon,
        "tickers_scored":   len(return_rows),
        "tickers_missing":  len(missing),
        "missing_tickers":  missing,
        "survivorship_note": (
            f"{len(missing)} tickers had no data at horizon — likely delisted/acquired. "
            "These are EXCLUDED from analysis, creating upward survivorship bias. "
            f"Bias magnitude: ~{len(missing)/max(len(records),1)*100:.1f}% of universe."
        ),
        "by_rating":  analysis,
        "by_bucket":  bucket_analysis,
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\n" + "=" * 70)
    print(f"RESULTS — {snapshot_date} @ {horizon}")
    print("=" * 70)
    print(f"\n  {'Rating':<25} {'N':>5} {'Mean Ret':>10} {'Median':>10} {'% Positive':>12}")
    print(f"  {'-'*25} {'-'*5} {'-'*10} {'-'*10} {'-'*12}")
    for rating, stats in analysis.items():
        print(
            f"  {rating:<25} {stats['count']:>5} "
            f"{stats['mean_return']*100:>9.1f}% "
            f"{stats['median_return']*100:>9.1f}% "
            f"{stats['positive_pct']*100:>11.0f}%"
        )

    print(f"\n  Survivorship note: {len(missing)} tickers excluded (no data at horizon)")
    if missing:
        print(f"    Missing: {', '.join(missing[:10])}{'...' if len(missing) > 10 else ''}")

    print(f"\n  Saved: {out_csv.name}  |  {out_json.name}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, help="Snapshot date (YYYY-MM-DD)")
    parser.add_argument("--horizon",  required=True, choices=list(HORIZON_DAYS), help="Return horizon")
    args = parser.parse_args()
    run(args.snapshot, args.horizon)
