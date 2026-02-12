from pathlib import Path
from dotenv import load_dotenv
import logging
import os

# Load .env file from backend folder
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from backend.database.connection import init_db, check_db_connection
from backend.routes.market import router as market_router
from backend.routes.peers import router as peers_router
from backend.routes.fundamentals import router as fundamentals_router
from backend.routes.sectors import router as sectors_router
from backend.routes.macro import router as macro_router
from backend.routes.network import router as network_router
from backend.routes.backtest import router as backtest_router
from backend.routes.research import router as research_router
from backend.routes.social import router as social_router
from backend.routes.eia_routes import router as eia_router
from backend.routes.insights_routes import router as insights_router
from backend.routes.reports_routes import router as reports_router
from backend.routes.fred_routes import router as fred_router
from backend.routes.treemap import router as treemap_router
from backend.routes.sentiment import router as sentiment_router
from backend.routes.emotion_advisor import router as emotion_advisor_router
from backend.routes.crowd_insight import router as crowd_insight_router
from backend.routes.backtest_agent import router as backtest_agent_router
from backend.finverse_integration.routes.wealth_routes import router as wealth_router
from backend.routes.chat import router as chat_router
from backend.routes.sector_intel import router as sector_intel_router

logger = logging.getLogger(__name__)

# --- Runtime Config ---
APP_ENV = os.getenv("APP_ENV", "development").lower()
ENABLE_DB = os.getenv("ENABLE_DB", "true").lower() == "true"
DB_REQUIRED = os.getenv("DB_REQUIRED", "false").lower() == "true"
DISABLE_DOCS = os.getenv("DISABLE_DOCS", "false").lower() == "true"

cors_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "")
cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
if not cors_origins and APP_ENV != "production":
    cors_origins = ["*"]
elif not cors_origins and APP_ENV == "production":
    logger.warning("⚠️ CORS_ALLOW_ORIGINS not set in production. CORS will be blocked.")

trusted_hosts_raw = os.getenv("TRUSTED_HOSTS", "")
trusted_hosts = [h.strip() for h in trusted_hosts_raw.split(",") if h.strip()]
if not trusted_hosts and APP_ENV != "production":
    trusted_hosts = ["*"]

app = FastAPI(
    title="Boomerang Backend",
    docs_url=None if DISABLE_DOCS else "/docs",
    redoc_url=None if DISABLE_DOCS else "/redoc",
    openapi_url=None if DISABLE_DOCS else "/openapi.json",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(market_router)
app.include_router(peers_router)
app.include_router(fundamentals_router)
app.include_router(sectors_router)
app.include_router(macro_router)
app.include_router(network_router)
app.include_router(backtest_router)
app.include_router(research_router)
app.include_router(social_router)
app.include_router(eia_router)
app.include_router(insights_router)
app.include_router(reports_router)
app.include_router(fred_router)
app.include_router(treemap_router)
app.include_router(sentiment_router)
app.include_router(emotion_advisor_router)
app.include_router(crowd_insight_router)
app.include_router(backtest_agent_router)
app.include_router(wealth_router)
app.include_router(chat_router)
app.include_router(sector_intel_router)

@app.on_event("startup")
def startup_init_db():
    """Initialize database - non-fatal if DB is unavailable"""
    if not ENABLE_DB:
        logger.info("🛑 DB init skipped (ENABLE_DB=false)")
        return

    try:
        logger.info("🗄️ Attempting database initialization...")
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Database not available: {e}")
        logger.warning("⚠️ Continuing without DB - agents and APIs remain functional")
        logger.info("💡 To enable DB: Ensure PostgreSQL is running on configured port")
        if DB_REQUIRED:
            raise

@app.get("/")
def health():
    return {"status": "ok"}

@app.get("/health")
def health_check():
    db_ok = check_db_connection() if ENABLE_DB else False
    return {
        "status": "ok",
        "env": APP_ENV,
        "db_enabled": ENABLE_DB,
        "db_ok": db_ok,
    }
