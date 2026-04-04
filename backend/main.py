from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import logging
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the expected .env location
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# --- Isolated Page-specific Modules (Page Router Pattern) ---
from backend.sectors.main import router as sectors_app
from backend.markets.main import router as markets_app
from backend.technical.main import router as technical_app
from backend.chat.main import router as chat_app
from backend.portfolio.main import router as portfolio_app
from backend.backtest.main import router as backtest_app

# --- New Isolated Modules ---
from backend.peers.main import router as peers_app
from backend.research.main import router as research_app
from backend.dashboard.main import router as dashboard_app
from backend.network.main import router as network_app
from backend.news.main import router as news_app
from backend.screener.main import router as screener_app
from backend.profile.main import router as profile_app
from backend.technical.fundamentals_service import get_fundamentals_summary

# FRED routes registered at /api level so /api/fred/* matches frontend api.ts
from backend.markets.fred_routes import router as fred_router

from backend.chat.core.pipeline import InvestmentPipeline

# Suppress noise
warnings.filterwarnings("ignore", category=FutureWarning, module=r"yfinance\..*")
warnings.filterwarnings(
    "ignore",
    message=r".*Timestamp\.utcnow is deprecated.*",
    category=Warning,
    module=r"yfinance\..*",
)

app = FastAPI(title="Agentic Investment OS")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    logging.error(f"Global Error Hook caught: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=200,
        content={
            "status": "error",
            "message": str(exc)
        }
    )



# CORS Configuration
default_origins = [
    "http://localhost:5173", 
    "http://localhost:5174", 
    "http://localhost:5175",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register Modular Apps ---
# Each module's router is registered with a unique prefix to prevent route collisions.
app.include_router(sectors_app,   prefix="/api/sectors",   tags=["Sectors"])
app.include_router(markets_app,   prefix="/api/markets",   tags=["Markets"])
app.include_router(technical_app, prefix="/api/technical", tags=["Technical"])
app.include_router(chat_app,      prefix="/api/chat",      tags=["Chat"])
app.include_router(portfolio_app, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(backtest_app,  prefix="/api/backtest",  tags=["Backtest"])
app.include_router(peers_app,     prefix="/api/peers",     tags=["Peers"])
app.include_router(research_app,  prefix="/api/research",  tags=["Research"])
app.include_router(dashboard_app, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(network_app,   prefix="/api/network",   tags=["Network"])
app.include_router(news_app,      prefix="/api/news",      tags=["News"])
app.include_router(screener_app,  prefix="/api/screener",  tags=["Screener"])
app.include_router(profile_app,   prefix="/api/profile",   tags=["Profile"])
# FRED at top-level /api so frontend /api/fred/* calls resolve correctly
app.include_router(fred_router,   prefix="/api",            tags=["FRED Data"])


@app.get("/api/fundamentals/summary/{symbol}")
def fundamentals_summary_compat(symbol: str):
    """Compatibility alias for legacy frontend bundles expecting /api/fundamentals/* routes."""
    data = get_fundamentals_summary(symbol)
    if not data or not data.get("name"):
        raise HTTPException(status_code=404, detail="Not found")
    return data

# Database Initialization
from backend.database.connection import init_db, run_init_sql
try:
    init_db()
    run_init_sql()
except Exception as e:
    print(f"Database init failed: {e}")

# Investment Pipeline
_pipeline = None
def _get_pipeline() -> InvestmentPipeline:
    global _pipeline
    if _pipeline is None: _pipeline = InvestmentPipeline()
    return _pipeline

@app.get("/health")
def health_check(): return {"status": "ok", "version": "2.2.0-modular"}

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            result = await _get_pipeline().run(
                query=msg.get("query"), 
                ticker=msg.get("ticker"), 
                market=msg.get("market", "us")
            )
            await websocket.send_json(result)
    except Exception as e:
        print(f"WS Error: {e}")
        try: await websocket.close()
        except: pass
