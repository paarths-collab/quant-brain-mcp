"""
Emotion-Safe Investment Advisor API Routes
Detects emotional bias and returns calming, data-backed guidance.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.emotion_advisor_service import analyze_emotion_safe_advice

router = APIRouter(prefix="/api/emotion-advisor", tags=["Emotion Safe Advisor"])


class EmotionAdvisorRequest(BaseModel):
    message: str = Field(..., description="User query or decision statement")
    tickers: Optional[List[str]] = Field(default=None, description="Optional list of tickers")
    market: Optional[str] = Field(default="us", description="Market: 'us' or 'india'")
    time_horizon_years: Optional[float] = Field(default=None, ge=0, description="Investment horizon in years")
    risk_tolerance: Optional[ str] = Field(default=None, description="low, medium, high")
    recent_action: Optional[str] = Field(default=None, description="'buy' or 'sell'")
    include_market_data: bool = Field(default=True, description="Include market context from price history")
    include_news: bool = Field(default=True, description="Include recent news sentiment")
    include_social_sentiment: bool = Field(default=False, description="Include Reddit/social media sentiment")
    include_comprehensive_scrape: bool = Field(default=False, description="Include full scrape (news, social, insider, analyst)")
    user_id: Optional[str] = Field(default=None, description="User identifier for cooldown tracking")
    check_cooldown: bool = Field(default=False, description="Check if user has active cooldown lock")
    auto_create_cooldown: bool = Field(default=False, description="Auto-create 24hr cooldown when high emotion detected")


@router.post("/analyze")
def analyze_emotion_advisor(request: EmotionAdvisorRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        return analyze_emotion_safe_advice(
            message=request.message,
            tickers=request.tickers,
            market=request.market or "us",
            time_horizon_years=request.time_horizon_years,
            risk_tolerance=request.risk_tolerance,
            recent_action=request.recent_action,
            include_market_data=request.include_market_data,
            include_news=request.include_news,
            include_social_sentiment=request.include_social_sentiment,
            include_comprehensive_scrape=request.include_comprehensive_scrape,
            user_id=request.user_id,
            check_cooldown=request.check_cooldown,
            auto_create_cooldown=request.auto_create_cooldown,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
