import math
import logging
import json
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body, BackgroundTasks
from pydantic import BaseModel

# Unified services
from backend.services.market_data import market_service
from backend.services.technical_analysis import technical_service

from .fred_service import FredDataService, ALL_DEFAULT_SERIES
from .eia_service import EIAService
from backend.database.connection import get_db_session
from backend.database.models import FredData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Markets & Macro"])

def _sanitize_for_json(value):
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception as exc:
            logger.debug("Failed to coerce scalar value %r: %s", value, exc)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(v) for v in value]
    return str(value)

# --- Market Data (Legacy /api/market) ---

@router.get("/overview")
@router.get("")
def get_market_data_overview():
    data = market_service.get_market_overview()
    return _sanitize_for_json({"indices": data})

@router.get("/candles/{symbol}")
def get_market_candles(
    symbol: str, 
    interval: str = Query("1d"), 
    range: str = Query("1y"),
    market: str = Query("US")
):
    """Fetch OHLCV candles with market safety."""
    data = market_service.fetch_candles(symbol, interval, range, market=market)
    if not data: 
        raise HTTPException(status_code=404, detail=f"No candle data found for {symbol} in {market} market")
    return {"symbol": symbol, "market": market, "data": data}

@router.get("/indicators/{symbol}")
def get_market_indicators(
    symbol: str, 
    interval: str = Query("1d"), 
    range: str = Query("1y"),
    market: str = Query("US")
):
    """Fetch technical indicators with market safety."""
    data = technical_service.calculate_indicators(symbol, range, interval, market=market)
    if not data: 
        raise HTTPException(status_code=404, detail=f"Failed to calculate indicators for {symbol}")
    return {"symbol": symbol, "market": market, "indicators": data}

# --- FRED Data (Cached and Live) ---
from .fred_routes import router as fred_router
router.include_router(fred_router)

# --- EIA Data (Legacy /api/eia) ---

@router.get("/eia/latest")
def get_eia_latest():
    """Returns a summary of petroleum data from EIA."""
    return EIAService().get_petroleum_summary()

# --- Macro (Legacy /api/macro) ---

@router.get("/macro/overview")
def get_macro_overview(db=Depends(get_db_session)):
    # Simulating macro overview by fetching key FRED indices
    fred = FredDataService(db)
    keys = ["GDP", "CPIAUCSL", "UNRATE"]
    return {k: fred.get_series_data(k, 30) for k in keys}

