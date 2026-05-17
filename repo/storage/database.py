"""
database.py — SQLite schema and connection helper.

The database stores historical snapshots of prices, financials, valuations,
news, and audit records. This lets you:
  - Avoid repeating API calls for data that hasn't changed
  - Track how valuations and decisions changed over time
  - See a full audit trail of where each data point came from

The database file is created automatically on first run.
It is stored in storage/pcc_data.db (excluded from git via .gitignore).
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "pcc_data.db"


def get_connection() -> sqlite3.Connection:
    """Open and return a SQLite connection. Rows behave like dictionaries."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create all database tables if they don't exist yet.
    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS everywhere.
    Called automatically when this module is first imported.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
    -- ── Price snapshots ───────────────────────────────────────────────────────
    -- One row per fetch. Keeps a history so you can see price changes.
    CREATE TABLE IF NOT EXISTS price_snapshots (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker      TEXT    NOT NULL,
        price       REAL,
        change_pct  REAL,           -- e.g. 0.0048 means +0.48%
        volume      INTEGER,
        market_cap  REAL,
        source      TEXT,           -- which provider delivered this
        fetched_at  TEXT NOT NULL   -- ISO 8601 UTC timestamp
    );

    -- ── Daily OHLCV candles ───────────────────────────────────────────────────
    -- UNIQUE on (ticker, date, source) so we don't store duplicates.
    CREATE TABLE IF NOT EXISTS candles (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker      TEXT    NOT NULL,
        date        TEXT    NOT NULL,  -- YYYY-MM-DD
        open        REAL,
        high        REAL,
        low         REAL,
        close       REAL,
        volume      INTEGER,
        source      TEXT,
        fetched_at  TEXT    NOT NULL,
        UNIQUE(ticker, date, source)
    );

    -- ── Financial statement snapshots ─────────────────────────────────────────
    -- Full statements stored as JSON so any field can be retrieved later.
    CREATE TABLE IF NOT EXISTS financials (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker         TEXT    NOT NULL,
        period         TEXT,           -- e.g. "2024-Q4" or "FY2024"
        statement_type TEXT,           -- income | balance | cashflow
        data_json      TEXT,           -- full statement as JSON string
        source         TEXT,
        fetched_at     TEXT    NOT NULL
    );

    -- ── Valuation outputs ─────────────────────────────────────────────────────
    -- Every time we run a valuation model, we save the result.
    -- This lets you see "MSFT fair value changed from $340 to $365 after Q4 earnings."
    CREATE TABLE IF NOT EXISTS valuation_outputs (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker         TEXT    NOT NULL,
        model          TEXT,           -- dcf | dividend | relative | composite
        fair_value     REAL,
        upside_pct     REAL,           -- (fair_value - price) / price
        confidence     REAL,           -- 0.0 to 1.0
        inputs_json    TEXT,           -- key assumptions (WACC, growth, etc.)
        warnings_json  TEXT,           -- list of warnings about data quality
        source         TEXT,
        calculated_at  TEXT    NOT NULL
    );

    -- ── News and events ───────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS news_events (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker       TEXT    NOT NULL,
        headline     TEXT,
        summary      TEXT,
        source       TEXT,             -- Benzinga | Finnhub | FMP | GDELT
        event_type   TEXT,             -- Earnings | Analyst | Filing | M&A | etc.
        sentiment    TEXT,             -- Positive | Negative | Neutral | Mixed
        impact       TEXT,             -- Low | Medium | High
        published_at TEXT,             -- when the article was published
        fetched_at   TEXT    NOT NULL
    );

    -- ── Macro snapshots ───────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS macro_snapshots (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id  TEXT    NOT NULL,   -- e.g. "DGS10" (FRED series ID)
        label      TEXT,               -- e.g. "10Y Treasury"
        value      REAL,
        source     TEXT,               -- FRED | Polygon
        period     TEXT,               -- date the value refers to
        fetched_at TEXT    NOT NULL
    );

    -- ── Source audit records ──────────────────────────────────────────────────
    -- Every data fetch writes an audit row so you can see data provenance.
    CREATE TABLE IF NOT EXISTS source_audits (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker        TEXT    NOT NULL,
        data_type     TEXT    NOT NULL,  -- price | fundamentals | news | macro | valuation
        provider_used TEXT,
        fallback_used INTEGER DEFAULT 0, -- 1 = primary failed, used a fallback
        confidence    REAL,              -- 0.0 to 100.0
        warnings_json TEXT,              -- JSON list of warning strings
        audited_at    TEXT    NOT NULL
    );

    -- ── API call log ──────────────────────────────────────────────────────────
    -- Low-level log of every external API call. Useful for debugging rate limits.
    CREATE TABLE IF NOT EXISTS api_call_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        provider    TEXT    NOT NULL,
        endpoint    TEXT,
        ticker      TEXT,
        status      TEXT,              -- success | error | timeout | rate_limited
        error_msg   TEXT,
        response_ms INTEGER,           -- how long the call took in milliseconds
        called_at   TEXT    NOT NULL
    );
    """)

    conn.commit()
    conn.close()


# ── Run schema creation on first import ──────────────────────────────────────
# CREATE TABLE IF NOT EXISTS is idempotent — safe to run every time.
init_db()
