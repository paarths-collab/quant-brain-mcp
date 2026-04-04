import json
import logging
import pandas as pd
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query

# Internal services
from .fundamentals_service import get_fundamentals_summary
from .peer_service import fetch_peer_comparison
from .peers_legacy_service import fetch_stock_peers

# Unified services
from backend.services.market_data import market_service
from .core.strategy_service import get_strategy, get_available_strategies
from .core.json_utils import make_json_safe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Technical & Fundamentals"])

# --- Technical Analysis (Legacy /api/technical) ---

@router.get("/technical/strategies")
async def get_strategies():
    return {"strategies": get_available_strategies()}

@router.get("/technical/analyze")
async def analyze_strategy(
    symbol: str,
    strategy: str,
    period: str = "1y",
    interval: str = "1d",
    market: str = "US",
    params: Optional[str] = Query(None)
):
    try:
        end_date = pd.Timestamp.now()
        period = period.lower()
        buffer = pd.DateOffset(days=365) 
        
        if period == "1m": start_date = end_date - pd.DateOffset(months=1) - buffer
        elif period == "3m": start_date = end_date - pd.DateOffset(months=3) - buffer
        elif period == "6m": start_date = end_date - pd.DateOffset(months=6) - buffer
        elif period == "1y": start_date = end_date - pd.DateOffset(years=1) - buffer
        elif period == "2y": start_date = end_date - pd.DateOffset(years=2) - buffer
        elif period == "5y": start_date = end_date - pd.DateOffset(years=5) - buffer
        elif period == "all": start_date = "1900-01-01"
        else: start_date = end_date - pd.DateOffset(years=2) - buffer 
        
        start_date_str = start_date.strftime('%Y-%m-%d') if isinstance(start_date, pd.Timestamp) else str(start_date)
        end_date_str = end_date.strftime('%Y-%m-%d')
            
        df = market_service.fetch_ohlcv(symbol, interval=interval, period=period, market=market)
        if df.empty: raise HTTPException(status_code=404, detail="No data")
            
        strategy_params = json.loads(params) if params else {}
        strategy_instance = get_strategy(strategy, **strategy_params)
        result = strategy_instance.analyze(df)
        
        # Trim results
        strict_start = end_date - pd.DateOffset(years=1) # simplified for brevity, should match legacy
        strict_start_str = strict_start.strftime('%Y-%m-%d')
        
        if "signals" in result:
            result["signals"] = [s for s in result["signals"] if s.get("date") >= strict_start_str]
        if "indicators" in result:
            result["indicators"] = {k: [d for d in v if d.get("time") >= strict_start_str] for k, v in result["indicators"].items()}
            
        return result
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Fundamentals (Legacy /api/fundamentals) ---

@router.get("/fundamentals/summary/{symbol}")
def get_fundamental_summary(symbol: str):
    data = get_fundamentals_summary(symbol)
    if not data or not data.get("name"):
        raise HTTPException(status_code=404, detail="Not found")
    return data

# --- Peers (Legacy /api/peers) ---

@router.get("/peers/compare/{symbol}")
def get_peer_comparison_route(symbol: str, limit: int = Query(12)):
    try:
        data = fetch_peer_comparison(symbol, limit=limit)
        return make_json_safe(data)
    except Exception as e:
        return make_json_safe({"symbol": symbol, "error": str(e), "rows": []})

@router.get("/peers/{symbol}")
def get_peers_route(symbol: str):
    peers = fetch_stock_peers(symbol)
    return {"symbol": symbol.upper(), "peers": peers, "count": len(peers)}
