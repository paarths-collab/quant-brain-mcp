from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.agents.orchestrator import Orchestrator
import backend.config as cfg

router = APIRouter(prefix="/api/insights", tags=["Insights Agent"])

# --- Helper to build config dict from backend.config ---
def build_orchestrator_config():
    return {
        "api_keys": {
            "finnhub": cfg.FINNHUB_API_KEY,
            "fred": cfg.FRED_API_KEY,
            "newsapi": cfg.NEWS_API_KEY,
            "reddit_client_id": cfg.REDDIT_CLIENT_ID,
            "reddit_client_secret": cfg.REDDIT_CLIENT_SECRET,
            "reddit_user_agent": cfg.REDDIT_USER_AGENT,
            "alpaca_key_id": cfg.ALPACA_KEY_ID,
            "alpaca_secret_key": cfg.ALPACA_SECRET_KEY,
            "openrouter": cfg.OPENROUTER_API_KEY,
            "openrouter1": cfg.OPENROUTER_API_KEY_1,
            "gemini": cfg.GEMINI_API_KEY
        },
        "agent_settings": {
            "paper_trading": True, # Default to paper trading
            "alpaca_base_url": cfg.ALPACA_BASE_URL
        },
        "rapidapi": {
            "key": cfg.RAPIDAPI_KEY,
            "hosts": cfg.RAPIDAPI_HOSTS
        }
    }

# Initialize orchestrator
try:
    orchestrator = Orchestrator(build_orchestrator_config())
except Exception as e:
    print(f"Error initializing Orchestrator: {e}")
    orchestrator = None

# --- Models ---
class AnalysisRequest(BaseModel):
    investor_type: str = Field(..., description="Type of analysis: 'ai_driven', 'long-term', 'short-term'")
    tickers: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class TradeRequest(BaseModel):
    ticker: str
    qty: float
    side: str = Field(..., description="'buy' or 'sell'")

# --- Endpoints ---

@router.post("/analyze")
def run_dynamic_analysis(request: AnalysisRequest):
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized found.")
        
    try:
        results = orchestrator.execute_analysis_flow(
            investor_type=request.investor_type,
            tickers=request.tickers,
            start_date=request.start_date,
            end_date=request.end_date
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trade/execute")
def execute_trade(request: TradeRequest):
    if not orchestrator:
         raise HTTPException(status_code=500, detail="Orchestrator not initialized.")
         
    try:
        order_result = orchestrator.execution_agent.submit_market_order(
            ticker=request.ticker,
            qty=request.qty,
            side=request.side
        )
        if "error" in order_result:
             raise HTTPException(status_code=400, detail=order_result["error"])
        return {"status": "success", "order_details": order_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account/info")
def get_account():
    if not orchestrator:
         raise HTTPException(status_code=500, detail="Orchestrator not initialized.")
    
    info = orchestrator.execution_agent.get_account_info()
    if "error" in info:
        raise HTTPException(status_code=500, detail=info["error"])
    return info

@router.get("/account/positions")
def get_positions():
    if not orchestrator:
         raise HTTPException(status_code=500, detail="Orchestrator not initialized.")
         
    positions = orchestrator.execution_agent.get_open_positions()
    if positions and isinstance(positions, list) and len(positions) > 0 and isinstance(positions[0], dict) and "error" in positions[0]:
         raise HTTPException(status_code=500, detail=positions[0]["error"])
    return positions
