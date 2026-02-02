from fastapi import APIRouter, HTTPException, Query
from backend.services.social_service import fetch_reddit_posts
from typing import Dict, Any

router = APIRouter(prefix="/api/social", tags=["Social Media"])

@router.get("/reddit/{symbol}")
def get_reddit_updates(
    symbol: str, 
    limit: int = Query(15, ge=5, le=50)
):
    """
    Get recent Reddit posts discussing the stock.
    """
    try:
        data = fetch_reddit_posts(symbol, limit)
        if "error" in data:
            # We don't raise 500 for config error, just return empty list with error msg
            return data
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
