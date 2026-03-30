import math
import logging
import json
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body, BackgroundTasks
from pydantic import BaseModel

from .data_service import fetch_candles, calculate_indicators, get_market_overview
from .fred_service import FredDataService, ALL_DEFAULT_SERIES, _fetch_gold_price_from_yf
from .eia_service import EIAService
from backend.database.connection import get_db_session
from backend.database.models import FredData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Markets & Macro"])

def _sanitize_for_json(value):
    if hasattr(value, "item"):
        try: value = value.item()
        except: pass
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

@router.get("/market/overview")
def get_market_data_overview():
    data = get_market_overview()
    return {"indices": data}

@router.get("/market/candles/{symbol}")
def get_market_candles(
    symbol: str, 
    interval: str = "1d", 
    range: str = "1y",
    market: str = "US"
):
    data = fetch_candles(symbol, interval, range, market=market)
    if not data: raise HTTPException(status_code=404, detail="Not found")
    return {"symbol": symbol, "data": data}

@router.get("/market/indicators/{symbol}")
def get_market_indicators(
    symbol: str, interval: str = "1d", range: str = "1y"
):
    data = calculate_indicators(symbol, range, interval)
    if not data: raise HTTPException(status_code=404, detail="Fail")
    return {"symbol": symbol, "indicators": data}

# --- FRED Data (Legacy /api/fred) ---

class SyncRequest(BaseModel):
    series_id: str
    series_type: str = "index"
    days: int = 365

@router.get("/fred/series")
def get_fred_series(db=Depends(get_db_session)):
    try:
        fred = FredDataService(db)
        return fred.get_all_series_metadata()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fred/data/{series_id}")
def get_fred_data(series_id: str, days: int = 365, db=Depends(get_db_session)):
    try:
        fred = FredDataService(db)
        data = fred.get_series_data(series_id, days)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fred/sync")
def sync_fred_series(req: SyncRequest, background_tasks: BackgroundTasks, db=Depends(get_db_session)):
    fred = FredDataService(db)
    background_tasks.add_task(fred.sync_series, req.series_id, req.series_type, req.days)
    return {"status": "Sync started", "series_id": req.series_id}

@router.get("/fred/gold-price")
def get_gold_price():
    # Helper for gold price from yfinance (moved logic from fred_routes.py)
    from .fred_service import _fetch_gold_price_from_yf # I'll assume it's there
    price = _fetch_gold_price_from_yf()
    if not price: raise HTTPException(status_code=404, detail="Gold price unavailable")
    return price

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
