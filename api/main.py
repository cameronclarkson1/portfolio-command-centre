"""
FastAPI layer for AI HedgeFund dashboard.
Wraps the existing Python services and exposes JSON endpoints
that the Next.js frontend calls at http://localhost:8000.

Start with:
    cd c:\\Users\\camer\\Investment_Research\\api
    uvicorn main:app --reload --port 8000
"""

import sys
import os
from contextlib import asynccontextmanager

# ── Add repo/ to Python path so we can import services, providers, config ──────
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'repo'))
sys.path.insert(0, REPO_DIR)

# ── Load API keys from repo/.env ───────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(REPO_DIR, '.env'))

# ── FastAPI app ────────────────────────────────────────────────────────────────
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.market    import router as market_router
from routes.news      import router as news_router
from routes.valuation import router as valuation_router
from routes.portfolio import router as portfolio_router
from routes.research  import router as research_router
from routes.settings     import router as settings_router
from routes.health       import router as health_router
from routes.watchlist_api    import router as watchlist_router
from routes.sharesight_auth  import router as sharesight_auth_router
from routes.scanner          import router as scanner_router
from routes.events           import router as events_router

# ── APScheduler — daily market-close scan ────────────────────────────────────

def _start_scheduler(app: FastAPI) -> None:
    try:
        import pytz
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from routes.scanner import run_daily_scan

        et = pytz.timezone("America/New_York")
        scheduler = BackgroundScheduler(timezone=pytz.utc)
        scheduler.add_job(
            run_daily_scan,
            trigger=CronTrigger(day_of_week="mon-fri", hour=16, minute=15, timezone=et),
            id="daily_scan",
            replace_existing=True,
            misfire_grace_time=300,  # allow up to 5 min late start
        )
        scheduler.start()
        app.state.scheduler = scheduler
        print("[scheduler] Daily scan scheduled: Mon-Fri at 4:15 PM ET")
    except Exception as e:
        print(f"[scheduler] Failed to start: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _start_scheduler(app)
    # Auto-scan on startup if no cached results exist (e.g. fresh Railway deploy)
    try:
        import threading
        from routes.scanner import RESULTS_FILE, run_daily_scan
        if not RESULTS_FILE.exists():
            print("[startup] No scan results found — triggering background scan")
            threading.Thread(target=run_daily_scan, daemon=True).start()
    except Exception as e:
        print(f"[startup] Auto-scan skipped: {e}")
    yield
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="AI HedgeFund API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(market_router,    prefix="/api/market",    tags=["market"])
app.include_router(news_router,      prefix="/api/news",      tags=["news"])
app.include_router(valuation_router, prefix="/api/valuation", tags=["valuation"])
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(research_router,  prefix="/api/research",  tags=["research"])
app.include_router(settings_router,   prefix="/api/settings",   tags=["settings"])
app.include_router(health_router,     prefix="/api/health",     tags=["health"])
app.include_router(watchlist_router,      prefix="/api/watchlist",        tags=["watchlist"])
app.include_router(sharesight_auth_router, prefix="/auth/sharesight",     tags=["auth"])
app.include_router(scanner_router,         prefix="/api/scanner",          tags=["scanner"])
app.include_router(events_router,          prefix="/api/events",           tags=["events"])


@app.get("/api/health")
def health():
    """Quick check that the API is running."""
    return {"status": "ok"}
