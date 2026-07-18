"""
Phase 0.2 - Data-availability audit.
Reports concretely what historical data is reachable and how far back.

Run: python -m backtest.phase0_data_audit
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'repo'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'repo', '.env'))

PROBE_TICKERS = ["AAPL", "KO", "VICI"]

def audit_price_history():
    print("\n--- A. PRICE HISTORY (yfinance) ---")
    import yfinance as yf
    results = {}
    for t in PROBE_TICKERS:
        try:
            hist = yf.download(t, period="max", auto_adjust=True, progress=False)
            if hist.empty:
                print(f"  {t}: NO DATA")
                continue
            start = hist.index[0].date()
            end   = hist.index[-1].date()
            years = round((end - start).days / 365.25, 1)
            divs  = yf.Ticker(t).dividends
            div_ok = not divs.empty
            print(f"  {t}: {start} to {end} ({years}y)  dividends={div_ok}  rows={len(hist)}")
            results[t] = {"start": str(start), "end": str(end), "years": years,
                          "dividends": div_ok, "rows": len(hist)}
        except Exception as e:
            print(f"  {t}: ERROR - {e}")
    print("  NOTE: yfinance returns adjusted prices (splits+divs baked in).")
    print("        Adjusted close is the correct series for total-return backtesting.")
    return results

def audit_fundamentals():
    print("\n--- B. FUNDAMENTALS (FMP) ---")
    FMP_BASE = "https://financialmodelingprep.com/api/v3"
    FMP_KEY  = os.getenv("FMP_API_KEY", "")
    import requests
    results = {}
    for t in ["AAPL", "KO"]:
        try:
            url = f"{FMP_BASE}/income-statement/{t}?limit=20&apikey={FMP_KEY}"
            r   = requests.get(url, timeout=10)
            r.raise_for_status()
            stmts = r.json()
            if not isinstance(stmts, list) or not stmts:
                print(f"  {t}: no statements returned")
                continue
            dates = sorted([s.get("date","") for s in stmts if s.get("date")])
            sample = stmts[0]
            print(f"  {t}: {len(stmts)} quarters, earliest={min(dates)}, latest={max(dates)}")
            print(f"    period_end={sample.get('date')}  filing={sample.get('fillingDate')}  accepted={sample.get('acceptedDate')}")
            print(f"    WARNING: FMP returns LATEST RESTATED figures, not as-originally-filed.")
            results[t] = {"quarters": len(stmts), "earliest": min(dates), "latest": max(dates)}
        except Exception as e:
            print(f"  {t}: ERROR - {e}")

    print("\n  Point-in-time fundamentals options:")
    print("    SEC EDGAR (XBRL): as-filed, free, needs XBRL parser")
    print("    Intrinio: point-in-time, ~$50/mo")
    print("    Compustat/CRSP: gold standard, institutional licence")
    print("  STATUS: Point-in-time fundamentals NOT available with current providers.")
    return results

def audit_universe():
    print("\n--- C. POINT-IN-TIME UNIVERSE ---")
    try:
        import pandas as pd
        from io import StringIO
        import requests
        r = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10
        )
        tables = pd.read_html(StringIO(r.text))
        print(f"  Wikipedia S&P 500: {len(tables[0])} current members (TODAY only)")
    except Exception as e:
        print(f"  Wikipedia fetch failed: {e}")

    print("\n  Historical/delisted universe options:")
    print("    Wikipedia: today's members only - NO delisted names, NO history")
    print("    S&P Dow Jones: official constituent history, requires licence")
    print("    Sharadar (Quandl): historical S&P 500 PIT, ~$50/mo")
    print("    CRSP: gold standard, institutional licence")
    print("  STATUS: Point-in-time constituent history NOT available.")
    print("  SURVIVORSHIP BIAS: A backtest on today's S&P 500 silently excludes")
    print("    companies removed (bankrupt, delisted, acquired) - inflates results.")

def audit_analyst_estimates():
    print("\n--- D. HISTORICAL ANALYST ESTIMATES ---")
    FMP_BASE = "https://financialmodelingprep.com/api/v3"
    FMP_KEY  = os.getenv("FMP_API_KEY", "")
    import requests
    try:
        url  = f"{FMP_BASE}/analyst-estimates/AAPL?limit=10&apikey={FMP_KEY}"
        r    = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, list) and data:
            dates = [d.get("date") for d in data[:5]]
            print(f"  FMP analyst estimates for AAPL: {len(data)} periods, sample dates={dates}")
            print(f"  WARNING: These are current consensus revised to today,")
            print(f"    NOT what analysts estimated at each historical date t.")
        else:
            print(f"  FMP analyst estimates: {data}")
    except Exception as e:
        print(f"  ERROR: {e}")
    print("  STATUS: True point-in-time analyst estimates NOT available.")
    print("  Consequence: DCF Stage-1 growth inputs in any pseudo-backtest will use")
    print("    today's estimated growth, not what was known at historical date t.")

def run():
    print("=" * 70)
    print("PHASE 0.2 - DATA AVAILABILITY AUDIT")
    print("=" * 70)

    price_results = audit_price_history()
    fund_results  = audit_fundamentals()
    audit_universe()
    audit_analyst_estimates()

    print("\n" + "=" * 70)
    print("PHASE 0.2 SUMMARY TABLE")
    print("=" * 70)
    rows = [
        ("Price history (adj. close)",     "YES - yfinance, 20+ years", "YES"),
        ("Dividends for total return",      "YES - yfinance",            "YES"),
        ("Fundamentals (historical)",       "PARTIAL - FMP ~5 years",    "NO  - restated only"),
        ("Point-in-time financials",        "NO",                        "N/A"),
        ("Delisted names / PIT universe",   "NO",                        "NO  - survivorship bias"),
        ("Historical analyst estimates",    "NO",                        "NO  - lookahead"),
        ("Historical sector membership",    "NO",                        "N/A"),
    ]
    print(f"  {'Data Component':<35} {'Available?':<25} {'Backtest safe?'}")
    print(f"  {'-'*35} {'-'*25} {'-'*20}")
    for name, avail, safe in rows:
        print(f"  {name:<35} {avail:<25} {safe}")

    out_path = os.path.join(os.path.dirname(__file__), "phase0_data_audit.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"price": price_results, "fundamentals": fund_results}, f, indent=2, default=str)
    print(f"\nAudit data saved to: {out_path}")

if __name__ == "__main__":
    run()
