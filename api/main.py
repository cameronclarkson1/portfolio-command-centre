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
from routes.watchlist_api import router as watchlist_router

app = FastAPI(title="AI HedgeFund API", version="1.0.0")

# CORS — allow the frontend origin (set CORS_ORIGIN in production env vars)
_cors_origins_raw = os.getenv("CORS_ORIGIN", "http://localhost:3000")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(market_router,    prefix="/api/market",    tags=["market"])
app.include_router(news_router,      prefix="/api/news",      tags=["news"])
app.include_router(valuation_router, prefix="/api/valuation", tags=["valuation"])
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(research_router,  prefix="/api/research",  tags=["research"])
app.include_router(settings_router,   prefix="/api/settings",   tags=["settings"])
app.include_router(health_router,     prefix="/api/health",     tags=["health"])
app.include_router(watchlist_router,  prefix="/api/watchlist",  tags=["watchlist"])


@app.get("/api/health")
def health():
    """Quick check that the API is running."""
    return {"status": "ok"}
