import logging
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from backend.database.connection import get_db
from .core.emotion_agent import EmotionAnalysisAgent
from .service import analyze_crowd_insight, get_market_sentiment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

_EMOTION_AGENT = EmotionAnalysisAgent()

# --- Request Models ---
class SentimentRequest(BaseModel):
    message: str = Field(..., description="User text to analyze for emotion")
    tickers: Optional[List[str]] = Field(default=None, description="Optional stock tickers")
    market: str = Field(default="us")

class CrowdInsightRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    market: Optional[str] = Field(default="us")
    include_insider: bool = Field(default=True)
    include_news: bool = Field(default=True)

# --- Routes ---

@router.post("/sentiment")
def analyze_dashboard_sentiment(request: SentimentRequest):
    """
    Combined sentiment and market mood analysis for the dashboard.
    """
    try:
        # This uses the isolated logic in service.py (Migrated from market_pulse.py)
        return get_market_sentiment(request.message, request.tickers, request.market)
    except Exception as e:
        logger.exception("Dashboard sentiment failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/crowd-insight")
def analyze_crowd_signal(request: CrowdInsightRequest):
    """
    Combines insider activity and news sentiment into a unified signal.
    """
    try:
        FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", ""); RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", ""); RAPIDAPI_HOSTS = {}
        return analyze_crowd_insight(
            ticker=request.ticker,
            market=request.market or "us",
            include_insider=request.include_insider,
            include_news=request.include_news,
            finnhub_key=FINNHUB_API_KEY,
            rapidapi_config={
                "key": RAPIDAPI_KEY,
                "hosts": RAPIDAPI_HOSTS,
            },
        )
    except Exception as e:
        logger.exception("Crowd insight failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sector-news")
def get_dashboard_sector_news(
    market: str = Query("US"),
    sector: Optional[str] = Query(None),
    limit: int = Query(20),
    db=Depends(get_db),
):
    """
    Fetch sector-wise news from DB for dashboard display.
    """
    try:
        # Logic remains similar but moved to this modular router
        query = "SELECT sector, title, url, source, snippet, published_at FROM sector_news_item WHERE UPPER(market) = :market"
        params = {"market": market.upper(), "limit": limit}
        if sector:
            query += " AND LOWER(sector) = LOWER(:sector)"
            params["sector"] = sector
        query += " ORDER BY published_at DESC NULLS LAST LIMIT :limit"
        
        rows = db.execute(text(query), params).mappings().all()
        grouped = {}
        for row in rows:
            r = dict(row)
            sec = r.get("sector", "Unknown")
            if r.get("published_at"): r["published_at"] = r["published_at"].isoformat()
            if sec not in grouped: grouped[sec] = []
            grouped[sec].append(r)

        return {"market": market.upper(), "total_items": len(rows), "sectors": grouped}
    except Exception as e:
        logger.exception("Sector news query failed")
        raise HTTPException(status_code=500, detail=str(e))

