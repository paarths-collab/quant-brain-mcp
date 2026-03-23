from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.super_agent_routes import router as super_agent_router
from backend.routes.sector_intel import router as sector_intel_router
from backend.routes.investor_profile import router as investor_profile_router
from backend.routes.market_pulse import router as market_pulse_router
from backend.routes.stock_advisor import router as stock_advisor_router
from backend.routes.backtest import router as backtest_router
from backend.routes.long_term_routes import router as long_term_router
from backend.routes.market import router as market_router
from backend.routes.sectors import router as sectors_router
from backend.routes.fundamentals import router as fundamentals_router
from backend.routes.sentiment import router as sentiment_router
from backend.routes.research import router as research_router
from backend.routes.peers import router as peers_router
from backend.routes.macro import router as macro_router
from backend.routes.social import router as social_router
from backend.routes.network import router as network_router
from backend.routes.technical_analysis import router as technical_router
from backend.routes.treemap import router as treemap_router
from backend.routes.reports_routes import router as reports_router
from backend.finverse_integration.routes.wealth_routes import router as wealth_router

from backend.engine.pipeline import InvestmentPipeline
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket")

app = FastAPI(title="Agentic Investment OS")

# CORS Configuration
origins = [
    "http://localhost:5173", # Frontend dev server
    "http://localhost:5174", # Alternative port
    "http://localhost:5175", # Alternative port
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.routes.fred_routes import router as fred_router

app.include_router(super_agent_router, prefix="/api")
app.include_router(sector_intel_router)
app.include_router(investor_profile_router)
app.include_router(market_pulse_router)
app.include_router(stock_advisor_router)
app.include_router(backtest_router)
app.include_router(fred_router)
app.include_router(long_term_router)
app.include_router(market_router)
app.include_router(sectors_router)
app.include_router(fundamentals_router)
app.include_router(sentiment_router)
app.include_router(research_router)
app.include_router(peers_router)
app.include_router(macro_router)
app.include_router(social_router)
app.include_router(network_router)
app.include_router(technical_router)
app.include_router(treemap_router)
app.include_router(reports_router)
app.include_router(wealth_router)

# Initialize Database
from backend.database.connection import init_db, run_init_sql
try:
    init_db()
    run_init_sql()
except Exception as e:
    logger.error(f"Database init failed: {e}")

# Initialize Pipeline
_pipeline: InvestmentPipeline | None = None


def _get_pipeline() -> InvestmentPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = InvestmentPipeline()
    return _pipeline

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "Agentic Investment OS"}

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WS data: {data}")
            
            # Simple parsing
            query = data
            ticker = None
            market = "us"
            request_id = None
            
            # Try parsing as JSON to get explicit ticker
            try:
                msg = json.loads(data)
                if isinstance(msg, dict):
                    query = msg.get("query", data)
                    ticker = msg.get("ticker", None)
                    market = msg.get("market", market) or market
                    request_id = msg.get("request_id", None)
            except:
                pass
            
            # If no ticker found in JSON, try to guess from query if short enough? 
            # Or just pass as is. The pipeline needs a ticker for Strategy Lab.
            # If ticker is None, pure research mode runs.
            
            try:
                result = await _get_pipeline().run(query=query, ticker=ticker, market=market)
                if isinstance(result, dict) and request_id:
                    result["request_id"] = request_id
                await websocket.send_json(result)
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                await websocket.send_json({"error": str(e), "request_id": request_id})
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
             await websocket.close()
        except:
            pass
