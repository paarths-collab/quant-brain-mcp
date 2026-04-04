"""
Sentiment Analysis API Routes
Endpoints for stock sentiment analysis with AI
"""
import math
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from .core.stock_sentiment_service import (
    analyze_stock_sentiment,
    analyze_multiple_stocks,
)

router = APIRouter(prefix="/sentiment", tags=["Sentiment Analysis"])


def _sanitize_floats(obj):
    """Recursively replace inf/nan floats with None so JSON serialisation works."""
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_floats(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


class SentimentRequest(BaseModel):
    symbol: str


class BatchSentimentRequest(BaseModel):
    symbols: List[str]


@router.get("/analyze/{symbol}")
async def get_sentiment_analysis(
    symbol: str,
    market: Optional[str] = Query(None, description="Market: 'india' or 'us'")
):
    """
    Get AI-powered sentiment analysis for a stock
    
    - US stocks: AAPL, MSFT, GOOGL
    - Indian stocks: RELIANCE.NS, TCS.NS, INFY.NS
    """
    # Add .NS suffix for Indian stocks if needed
    if market and market.lower() == 'india' and '.NS' not in symbol.upper() and '.BO' not in symbol.upper():
        symbol = f"{symbol}.NS"
    
    try:
        result = analyze_stock_sentiment(symbol)
        
        if "error" in result and result.get("market_data") is None:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return _sanitize_floats(result)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error analyzing sentiment for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")


@router.post("/analyze")
async def post_sentiment_analysis(request: SentimentRequest):
    """
    POST endpoint for sentiment analysis
    """
    try:
        result = analyze_stock_sentiment(request.symbol)
        
        if "error" in result and result.get("market_data") is None:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return _sanitize_floats(result)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in POST sentiment analysis for {request.symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")


@router.post("/batch")
async def batch_sentiment_analysis(request: BatchSentimentRequest):
    """
    Analyze multiple stocks at once (max 10)
    """
    if len(request.symbols) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 symbols allowed per batch")
    
    try:
        results = analyze_multiple_stocks(request.symbols)
        return _sanitize_floats({
            "count": len(results),
            "results": results,
        })
    except Exception as e:
        import traceback
        print(f"Error in batch sentiment analysis: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@router.get("/quick/{symbol}")
async def get_quick_sentiment(
    symbol: str,
    market: Optional[str] = Query(None, description="Market: 'india' or 'us'")
):
    """
    Quick sentiment check (minimal data, faster response)
    Returns just outlook, sentiment score, and recommendation
    """
    if market and market.lower() == 'india' and '.NS' not in symbol.upper() and '.BO' not in symbol.upper():
        symbol = f"{symbol}.NS"
    
    try:
        result = analyze_stock_sentiment(symbol)
        
        if "error" in result and result.get("market_data") is None:
            raise HTTPException(status_code=404, detail=result["error"])
        
        # Return minimal data
        return _sanitize_floats({
            "symbol": result.get("symbol"),
            "name": result.get("name"),
            "market": result.get("market"),
            "price": result.get("price"),
            "outlook": result.get("outlook"),
            "sentiment": result.get("sentiment"),
            "recommendation": result.get("recommendation"),
            "targetPrice": result.get("targetPrice"),
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in quick sentiment analysis for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Quick analysis failed: {str(e)}")
