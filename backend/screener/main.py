import logging
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from .service import ScreenerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screener", tags=["Screener"])

_SERVICE = ScreenerService()

@router.get("/scan")
def run_momentum_screener(
    timeframe: str = Query("1d", enum=["1d", "1h", "15m"]),
    market: str = Query("india")
):
    """
    Scans the Nifty 50 universe for momentum + volume breakout candidates.
    Supports daily (swing), hourly (intraday), and 15m timeframes.
    """
    try:
        results = _SERVICE.run_scan(timeframe=timeframe)
        return {
            "status": "success",
            "count": len(results),
            "candidates": results,
            "market": "NSE",
            "as_of": results[0]["as_of"] if results else None
        }
    except Exception as e:
        logger.exception("Screener failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/watchlist")
def get_watchlist():
    """Returns the current screener watchlist."""
    from .service import WATCHLIST
    return {"watchlist": WATCHLIST}