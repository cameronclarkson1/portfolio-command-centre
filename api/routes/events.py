"""
Events route — macro economic calendar for 2026.
Returns upcoming FOMC, CPI, PCE, and Jobs Report dates
filtered to only include today and future events.
"""

from fastapi import APIRouter
from datetime import date

router = APIRouter()

# Hardcoded 2026 macro calendar (these dates are publicly known in advance)
_MACRO_2026 = [
    {"date": "2026-07-15", "event": "US CPI (Jun)",              "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-07-29", "event": "FOMC Meeting Day 1",         "time": "All Day",     "importance": "high"},
    {"date": "2026-07-30", "event": "FOMC Rate Decision",         "time": "2:00 PM ET",  "importance": "high"},
    {"date": "2026-07-31", "event": "US PCE Inflation (Jun)",     "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-08-07", "event": "US Jobs Report (Jul)",       "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-08-13", "event": "US CPI (Jul)",               "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-08-29", "event": "US PCE Inflation (Jul)",     "time": "8:30 AM ET",  "importance": "medium"},
    {"date": "2026-09-04", "event": "US Jobs Report (Aug)",       "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-09-10", "event": "US CPI (Aug)",               "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-09-15", "event": "FOMC Meeting Day 1",         "time": "All Day",     "importance": "high"},
    {"date": "2026-09-16", "event": "FOMC Rate Decision",         "time": "2:00 PM ET",  "importance": "high"},
    {"date": "2026-09-26", "event": "US PCE Inflation (Aug)",     "time": "8:30 AM ET",  "importance": "medium"},
    {"date": "2026-10-02", "event": "US Jobs Report (Sep)",       "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-10-15", "event": "US CPI (Sep)",               "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-10-30", "event": "US PCE Inflation (Sep)",     "time": "8:30 AM ET",  "importance": "medium"},
    {"date": "2026-11-04", "event": "FOMC Meeting Day 1",         "time": "All Day",     "importance": "high"},
    {"date": "2026-11-05", "event": "FOMC Rate Decision",         "time": "2:00 PM ET",  "importance": "high"},
    {"date": "2026-11-06", "event": "US Jobs Report (Oct)",       "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-11-13", "event": "US CPI (Oct)",               "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-11-25", "event": "US PCE Inflation (Oct)",     "time": "8:30 AM ET",  "importance": "medium"},
    {"date": "2026-12-04", "event": "US Jobs Report (Nov)",       "time": "8:30 AM ET",  "importance": "high"},
    {"date": "2026-12-09", "event": "FOMC Meeting Day 1",         "time": "All Day",     "importance": "high"},
    {"date": "2026-12-10", "event": "FOMC Rate Decision / CPI",   "time": "2:00 PM ET",  "importance": "high"},
    {"date": "2026-12-18", "event": "US PCE Inflation (Nov)",     "time": "8:30 AM ET",  "importance": "medium"},
]


@router.get("/macro")
def get_macro_events():
    """Return upcoming macro economic events from today onwards."""
    today = date.today().isoformat()
    upcoming = [e for e in _MACRO_2026 if e["date"] >= today]
    return {"events": upcoming}
