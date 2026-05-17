"""
cache_manager.py — Two-level cache: in-memory (fast) + SQLite (persistent).

How it works:
  1. On get(key, ttl): check memory first (instant), then SQLite (fast).
     If found and not stale, return immediately without calling any API.
  2. On set(key, value, ttl): write to both memory and SQLite.
  3. Memory cache is lost on app restart. SQLite cache survives restarts.

This means:
  - First load after restart: reads from SQLite (fast, no API call if fresh)
  - Subsequent loads in same session: reads from memory (instant)
  - After TTL expires: fetches fresh data from the API, then re-caches

Usage:
    from storage.cache_manager import cache
    from config.settings import CACHE_TTL

    data = cache.get("price:MSFT", ttl=CACHE_TTL["live_price"])
    if data is None:
        data = fetch_from_api()
        cache.set("price:MSFT", data, ttl=CACHE_TTL["live_price"])
"""

import json
import sqlite3
from datetime import datetime
from typing import Any

from utils.date_utils import is_stale, now_utc
from storage.database import DB_PATH


class CacheManager:

    def __init__(self):
        # In-memory store: key → (value, stored_at_datetime)
        self._memory: dict[str, tuple[Any, datetime]] = {}
        self._ensure_cache_table()

    def _ensure_cache_table(self):
        """Create the cache table if it doesn't exist."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key         TEXT PRIMARY KEY,
                value_json  TEXT    NOT NULL,
                stored_at   TEXT    NOT NULL,   -- ISO 8601 UTC
                ttl_seconds INTEGER NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get(self, key: str, ttl: int) -> Any | None:
        """
        Retrieve a cached value.

        Returns the cached value if it exists and is younger than ttl seconds.
        Returns None if the value is missing or stale.
        """
        # 1. Check in-memory cache (fastest path)
        if key in self._memory:
            value, stored_at = self._memory[key]
            if not is_stale(stored_at, ttl):
                return value
            # Stale in memory — remove and fall through to SQLite check
            del self._memory[key]

        # 2. Check SQLite cache (survives app restarts)
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT value_json, stored_at, ttl_seconds FROM cache WHERE key = ?",
            (key,)
        ).fetchone()
        conn.close()

        if row:
            stored_at = datetime.fromisoformat(row[1])
            # Use the smaller of the requested TTL and the stored TTL
            effective_ttl = min(ttl, row[2])
            if not is_stale(stored_at, effective_ttl):
                value = json.loads(row[0])
                # Promote back to memory cache for speed
                self._memory[key] = (value, stored_at)
                return value

        return None

    def set(self, key: str, value: Any, ttl: int):
        """
        Store a value in both the in-memory and SQLite caches.
        The value must be JSON-serialisable (dicts, lists, strings, numbers).
        """
        stored_at = now_utc()

        # Write to memory
        self._memory[key] = (value, stored_at)

        # Write to SQLite (INSERT OR REPLACE updates if key already exists)
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """
            INSERT OR REPLACE INTO cache (key, value_json, stored_at, ttl_seconds)
            VALUES (?, ?, ?, ?)
            """,
            (key, json.dumps(value, default=str), stored_at.isoformat(), ttl),
        )
        conn.commit()
        conn.close()

    def invalidate(self, key: str):
        """Remove a single key from both caches."""
        self._memory.pop(key, None)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()

    def invalidate_prefix(self, prefix: str):
        """
        Remove all keys that start with a given prefix.
        Useful for clearing all data for one ticker: invalidate_prefix("MSFT:")
        """
        self._memory = {k: v for k, v in self._memory.items() if not k.startswith(prefix)}
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM cache WHERE key LIKE ?", (prefix + "%",))
        conn.commit()
        conn.close()

    def stats(self) -> dict:
        """Return basic cache statistics (useful for the debug/admin panel)."""
        conn = sqlite3.connect(DB_PATH)
        total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        conn.close()
        return {
            "memory_entries": len(self._memory),
            "sqlite_entries": total,
        }


# ── Singleton — import and use this everywhere ────────────────────────────────
cache = CacheManager()
