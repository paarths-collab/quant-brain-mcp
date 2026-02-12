"""
Crowd Insight Signal API Routes
Combines insider activity and news sentiment into a unified signal.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

import backend.config as cfg
from backend.services.crowd_insight_service import analyze_crowd_insight

router = APIRouter(prefix="/api/crowd-insight", tags=["Crowd Insight"])


class CrowdInsightRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    market: Optional[str] = Field(default="us", description="Market: 'us' or 'india'")
    include_insider: bool = Field(default=True, description="Include insider activity signals")
    include_news: bool = Field(default=True, description="Include news sentiment signals")


@router.post("/analyze")
def analyze_crowd_signal(request: CrowdInsightRequest):
    if not request.ticker.strip():
        raise HTTPException(status_code=400, detail="Ticker cannot be empty.")

    try:
        return analyze_crowd_insight(
            ticker=request.ticker,
            market=request.market or "us",
            include_insider=request.include_insider,
            include_news=request.include_news,
            finnhub_key=cfg.FINNHUB_API_KEY,
            rapidapi_config={
                "key": cfg.RAPIDAPI_KEY,
                "hosts": cfg.RAPIDAPI_HOSTS,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
