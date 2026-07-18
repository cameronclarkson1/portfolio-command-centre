"""
snapshot_runner.py — Design B prospective backtest: Day-0 universe snapshot.

Scores every ticker in the S&P 500 today and persists the result so forward
returns can be appended at T+1M, T+3M, T+6M, T+12M checkpoints.

Output files (in backtest/snapshots/):
  snapshot_YYYY-MM-DD.jsonl   — one JSON record per ticker, append-friendly
  snapshot_YYYY-MM-DD.csv     — flat summary for Excel / pandas

Usage:
  python -m backtest.snapshot_runner              # full S&P 500 run
  python -m backtest.snapshot_runner --limit 20   # test run (first N tickers)
  python -m backtest.snapshot_runner --resume     # skip tickers already in today's file

Estimated runtime: ~25 min for full S&P 500 at 3s/ticker.
The run is resumable: interrupt and restart with --resume at any time.
"""

import sys, os, json, csv, time, argparse
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'repo'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'repo', '.env'))

import yfinance as yf
import providers.fmp_provider as fmp
from services.valuation_engine import run_valuation
from utils.logging_utils import get_logger

log = get_logger(__name__)

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
SLEEP_BETWEEN = 2.5   # seconds between tickers — FMP free tier pacing

CSV_FIELDS = [
    "snapshot_date", "ticker", "price", "sector", "bucket",
    "rating", "upside_pct", "fair_value_low", "fair_value_base", "fair_value_high",
    "overall_confidence", "models_ok", "models_na", "error",
]


def get_universe() -> list[str]:
    """Fetch current S&P 500 constituents from FMP, fall back to yfinance Wikipedia scrape."""
    try:
        tickers = fmp.get_index_constituents("sp500")
        if tickers:
            log.info(f"Universe: {len(tickers)} tickers from FMP S&P 500 constituent list")
            return sorted(tickers)
    except Exception as e:
        log.warning(f"FMP constituent list failed: {e} — falling back to Wikipedia")

    try:
        import pandas as pd
        from io import StringIO
        import requests
        r = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15,
        )
        tables = pd.read_html(StringIO(r.text))
        tickers = tables[0]["Symbol"].tolist()
        tickers = [t.replace(".", "-") for t in tickers]   # BRK.B → BRK-B
        log.info(f"Universe: {len(tickers)} tickers from Wikipedia S&P 500 (survivorship-biased)")
        return sorted(tickers)
    except Exception as e:
        raise RuntimeError(f"Both universe sources failed: {e}")


def get_price(ticker: str) -> float | None:
    """Fetch latest price via yfinance fast_info, fall back to recent close."""
    try:
        info = yf.Ticker(ticker).fast_info
        price = getattr(info, "last_price", None)
        if price and price > 0:
            return round(float(price), 4)
    except Exception:
        pass
    try:
        hist = yf.download(ticker, period="2d", progress=False, auto_adjust=True)
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 4)
    except Exception:
        pass
    return None


def score_ticker(ticker: str, price: float) -> dict:
    """Run valuation and return a flat record suitable for CSV + JSONL storage."""
    result = run_valuation(ticker, price)

    models_run = result.get("models_run", {})
    models_ok  = [k for k, v in models_run.items() if v.get("fair_value") is not None]
    models_na  = [k for k, v in models_run.items() if v.get("fair_value") is None]

    return {
        # Snapshot metadata
        "snapshot_date":      date.today().isoformat(),
        "scored_at":          datetime.now(timezone.utc).isoformat(),
        # Identity
        "ticker":             ticker,
        "price":              price,
        "sector":             result.get("sector", ""),
        "industry":           result.get("industry", ""),
        "bucket":             result.get("bucket", ""),
        # Valuation output
        "rating":             result.get("valuation_rating", ""),
        "upside_pct":         result.get("upside_pct"),
        "fair_value_low":     result.get("fair_value_low"),
        "fair_value_base":    result.get("fair_value_base"),
        "fair_value_high":    result.get("fair_value_high"),
        "overall_confidence": result.get("overall_confidence"),
        # Model coverage
        "models_ok":          ",".join(sorted(models_ok)),
        "models_na":          ",".join(sorted(models_na)),
        "model_count_ok":     len(models_ok),
        # Full detail for forward-return joins
        "_models_detail":     {
            k: {
                "fair_value": v.get("fair_value"),
                "confidence": v.get("confidence"),
            }
            for k, v in models_run.items()
        },
        "error":              None,
    }


def load_done_tickers(jsonl_path: Path) -> set[str]:
    """Return set of tickers already written to today's snapshot file."""
    done = set()
    if not jsonl_path.exists():
        return done
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("ticker"):
                    done.add(rec["ticker"])
            except json.JSONDecodeError:
                pass
    return done


def write_csv_summary(jsonl_path: Path, csv_path: Path) -> None:
    """Rewrite the CSV summary from the current JSONL file."""
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def run(limit: int | None = None, resume: bool = False) -> None:
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    today        = date.today().isoformat()
    jsonl_path   = SNAPSHOT_DIR / f"snapshot_{today}.jsonl"
    csv_path     = SNAPSHOT_DIR / f"snapshot_{today}.csv"

    print("=" * 70)
    print(f"DESIGN B SNAPSHOT — {today}")
    print(f"  Output: {jsonl_path}")
    print("=" * 70)

    universe = get_universe()
    if limit:
        universe = universe[:limit]
        print(f"  [TEST MODE] Limited to first {limit} tickers")

    done = load_done_tickers(jsonl_path) if resume else set()
    remaining = [t for t in universe if t not in done]

    if done:
        print(f"  Resuming: {len(done)} already done, {len(remaining)} remaining")

    total = len(universe)
    scored = len(done)
    errors = 0

    with open(jsonl_path, "a", encoding="utf-8") as jsonl_f:
        for i, ticker in enumerate(remaining, start=1):
            pct = round((scored / total) * 100, 1)
            print(f"  [{scored+1:>3}/{total}  {pct:>5.1f}%]  {ticker:<8}", end="  ", flush=True)

            try:
                price = get_price(ticker)
                if not price:
                    rec = {
                        "snapshot_date": today, "ticker": ticker,
                        "price": None, "error": "no_price",
                        "scored_at": datetime.now(timezone.utc).isoformat(),
                    }
                    print("NO PRICE")
                    errors += 1
                else:
                    rec = score_ticker(ticker, price)
                    rating  = rec.get("rating", "?")
                    upside  = rec.get("upside_pct")
                    n_ok    = rec.get("model_count_ok", 0)
                    upside_s = f"{upside*100:+.1f}%" if upside is not None else "N/A"
                    print(f"${price:<7.2f}  {rating:<22}  {upside_s:<8}  models_ok={n_ok}")

                jsonl_f.write(json.dumps(rec, default=str) + "\n")
                jsonl_f.flush()
                scored += 1

            except Exception as e:
                rec = {
                    "snapshot_date": today, "ticker": ticker,
                    "error": str(e)[:200],
                    "scored_at": datetime.now(timezone.utc).isoformat(),
                }
                jsonl_f.write(json.dumps(rec, default=str) + "\n")
                jsonl_f.flush()
                print(f"ERROR: {e}")
                errors += 1
                scored += 1

            # Refresh CSV every 25 tickers
            if scored % 25 == 0:
                write_csv_summary(jsonl_path, csv_path)

            time.sleep(SLEEP_BETWEEN)

    # Final CSV
    write_csv_summary(jsonl_path, csv_path)

    # Summary
    all_records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            try:
                all_records.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    ok_recs = [r for r in all_records if r.get("rating") and not r.get("error")]
    rating_counts = {}
    for r in ok_recs:
        rating_counts[r["rating"]] = rating_counts.get(r["rating"], 0) + 1

    print("\n" + "=" * 70)
    print(f"SNAPSHOT COMPLETE — {today}")
    print(f"  Tickers scored: {len(ok_recs)}/{total}   Errors: {errors}")
    print(f"  Files: {jsonl_path.name}  |  {csv_path.name}")
    print("\n  Rating distribution:")
    for rating, count in sorted(rating_counts.items(), key=lambda x: -x[1]):
        pct = count / len(ok_recs) * 100
        print(f"    {rating:<25} {count:>4}  ({pct:.1f}%)")
    print("=" * 70)
    print(f"\n  Next steps:")
    print(f"    T+1M  ({date.today().replace(month=date.today().month % 12 + 1) if date.today().month < 12 else date.today().replace(year=date.today().year+1, month=1)}): run forward_returns.py --snapshot {today} --horizon 1m")
    print(f"    T+3M  : run forward_returns.py --snapshot {today} --horizon 3m")
    print(f"    T+6M  : run forward_returns.py --snapshot {today} --horizon 6m")
    print(f"    T+12M : run forward_returns.py --snapshot {today} --horizon 12m")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Design B prospective snapshot runner")
    parser.add_argument("--limit", type=int, default=None, help="Limit to first N tickers (for testing)")
    parser.add_argument("--resume", action="store_true", help="Skip tickers already in today's snapshot file")
    args = parser.parse_args()
    run(limit=args.limit, resume=args.resume)
