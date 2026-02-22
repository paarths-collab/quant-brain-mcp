from fastapi import APIRouter, HTTPException, Query
from backend.services.market_data_service import fetch_candles, calculate_indicators, get_market_overview

router = APIRouter(prefix="/api/market", tags=["Market Data"])

@router.get("/overview")
def get_overview():
    """
    Returns market overview data (Indices).
    """
    data = get_market_overview()
    # Even if empty, return it (frontend handles empty state)
    return {"indices": data}

@router.get("/candles/{symbol}")
def get_candles(
    symbol: str, 
    interval: str = "1d", 
    range: str = "1y",
    market: str = "US"
):
    """
    Returns OHLCV data formatted for D3 charts.
    """
    data = fetch_candles(symbol, interval, range, market=market)
    if not data:
        raise HTTPException(status_code=404, detail="Data not found")
    return {"symbol": symbol, "data": data}

@router.get("/indicators/{symbol}")
def get_indicators(
    symbol: str,
    interval: str = "1d", 
    range: str = "1y"
):
    """
    Returns calculated technical indicators (RSI, MACD, etc.).
    """
    data = calculate_indicators(symbol, range, interval)
    if not data:
        raise HTTPException(status_code=404, detail="Indicators could not be calculated")
    return {"symbol": symbol, "indicators": data}
