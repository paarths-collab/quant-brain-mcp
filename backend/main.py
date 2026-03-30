from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import logging
import warnings
from pathlib import Path

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

from backend.chat.core.pipeline import InvestmentPipeline

# Suppress noise
warnings.filterwarnings("ignore", category=FutureWarning, module=r"yfinance\..*")

app = FastAPI(title="Agentic Investment OS")

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
# Each module's main.py provides a router with its own internal prefixes
app.include_router(sectors_app)
app.include_router(markets_app)
app.include_router(technical_app)
app.include_router(chat_app)
app.include_router(portfolio_app)
app.include_router(backtest_app)
app.include_router(peers_app)
app.include_router(research_app)
app.include_router(dashboard_app)
app.include_router(network_app)
app.include_router(news_app)
app.include_router(screener_app)
app.include_router(profile_app)

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
