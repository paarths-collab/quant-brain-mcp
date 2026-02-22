from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import json
import pandas as pd
from backend.services.data_loader import get_data
from backend.services.strategy_register import get_strategy, get_available_strategies

router = APIRouter(prefix="/api/technical", tags=["Technical Analysis"])

@router.get("/strategies")
async def get_strategies():
    """Return list of available strategies and their default parameters."""
    return {"strategies": get_available_strategies()}

@router.get("/analyze")
async def analyze_strategy(
    symbol: str,
    strategy: str,
    period: str = "1y",
    interval: str = "1d",
    market: str = "US",
    params: Optional[str] = Query(None, description="JSON string of strategy parameters")
):
    """
    Run a specific strategy on a symbol.
    """
    try:
        # 1. Fetch Data
        # Map period to start_date/end_date logic or let get_data handle it?
        # Assuming get_data handles 'period' or we need to convert.
        # fast_unification of get_data usually takes start/end.
        # Let's simple use a fixed lookback for now or calculate from period if needed.
        # For now, let's fetch 2 years to be safe for 200 SMA.
        
        # TODO: Better date handling based on period
        end_date = pd.Timestamp.now()
        
        # Parse Period
        period = period.lower()
        
        # Buffer to ensure indicators (like 200 SMA) have enough data
        buffer = pd.DateOffset(days=365) 
        
        if period == "1m":
            start_date = end_date - pd.DateOffset(months=1) - buffer
        elif period == "3m":
            start_date = end_date - pd.DateOffset(months=3) - buffer
        elif period == "6m":
            start_date = end_date - pd.DateOffset(months=6) - buffer
        elif period == "1y":
            start_date = end_date - pd.DateOffset(years=1) - buffer
        elif period == "2y":
            start_date = end_date - pd.DateOffset(years=2) - buffer
        elif period == "5y":
            start_date = end_date - pd.DateOffset(years=5) - buffer
        elif period == "all":
            start_date = "1900-01-01" # Let loader handle earliest date
        else:
            # Default fallback
            start_date = end_date - pd.DateOffset(years=2) - buffer 
        
        # Convert to string format YYYY-MM-DD to ensure yfinance compatibility
        if isinstance(start_date, pd.Timestamp):
            start_date_str = start_date.strftime('%Y-%m-%d')
        else:
            start_date_str = str(start_date)
            
        if isinstance(end_date, pd.Timestamp):
            end_date_str = end_date.strftime('%Y-%m-%d')
        else:
            end_date_str = str(end_date)
            
        print(f"DEBUG Analysis: Fetching {symbol} ({market}) from {start_date_str} to {end_date_str}")
        
        df = get_data(symbol, start=start_date_str, end=end_date_str, market=market)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found for symbol")
            
        # 2. Parse Parameters
        strategy_params = {}
        if params:
            try:
                strategy_params = json.loads(params)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in params")
                
        # 3. Get and Run Strategy
        strategy_instance = get_strategy(strategy, **strategy_params)
        result = strategy_instance.analyze(df)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        # 4. Trim Results to requested period (remove buffer)
        # We want to show only the requested range on the chart, not the buffer used for calculation.
        
        # Recalculate strict_start based on period logic (inverse of above)
        strict_start = end_date # Default
        if period == "1m": strict_start = end_date - pd.DateOffset(months=1)
        elif period == "3m": strict_start = end_date - pd.DateOffset(months=3)
        elif period == "6m": strict_start = end_date - pd.DateOffset(months=6)
        elif period == "1y": strict_start = end_date - pd.DateOffset(years=1)
        elif period == "2y": strict_start = end_date - pd.DateOffset(years=2)
        elif period == "5y": strict_start = end_date - pd.DateOffset(years=5)
        elif period == "all": strict_start = pd.Timestamp("1900-01-01")
        else: strict_start = end_date - pd.DateOffset(years=2)
        
        strict_start_str = strict_start.strftime('%Y-%m-%d')
        
        # Filter Signals
        if "signals" in result:
            result["signals"] = [
                s for s in result["signals"] 
                if s.get("date") >= strict_start_str
            ]
            
        # Filter Indicators
        if "indicators" in result:
            trimmed_indicators = {}
            for ind_name, ind_data in result["indicators"].items():
                trimmed_indicators[ind_name] = [
                    d for d in ind_data
                    if d.get("time") >= strict_start_str
                ]
            result["indicators"] = trimmed_indicators
            
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
