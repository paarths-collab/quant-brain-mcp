"""
Long Term Strategy Routes

Exposes endpoints for running long-term investment analysis (DCA, Dividend, Growth, Value).
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.services.long_term_strategy import run_long_term_strategy

router = APIRouter(prefix="/api/long-term", tags=["Long Term Strategy"])

class LongTermAnalysisRequest(BaseModel):
    ticker: str
    market: str = "US"
    risk_profile: str = "moderate"
    capital: float = 10000.0
    monthly_investment: float = 500.0
    start_date: str = "2020-01-01"
    end_date: Optional[str] = None # Defaults to today if None

@router.post("/analyze")
async def analyze_long_term(request: LongTermAnalysisRequest):
    """
    Run a comprehensive long-term analysis based on the selected risk profile.
    """
    try:
        from datetime import datetime
        end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")

        results = run_long_term_strategy(
            ticker=request.ticker,
            start=request.start_date,
            end=end_date,
            market=request.market,
            capital=request.capital,
            risk_profile=request.risk_profile,
            monthly_investment=request.monthly_investment
        )
        
        return {
            "status": "success",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
