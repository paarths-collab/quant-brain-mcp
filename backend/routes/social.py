from fastapi import APIRouter, HTTPException, Query
from backend.services.social_service import fetch_reddit_posts
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json

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


@router.get("/news")
def get_news_updates(
    query: str = Query("stock market news", min_length=1),
    limit: int = Query(12, ge=3, le=30),
    max_age_hours: int = Query(6, ge=1, le=24)
):
    """
    Get recent news headlines via DuckDuckGo News.
    """
    try:
        from backend.services.news_service import news_service
        
        # NewsService handles caching and rate limiting
        articles = news_service.get_news(query, limit)
        
        formatted_articles = []
        for item in articles:
            formatted_articles.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "date": item.get("date"),
                "summary": item.get("body"),
            })

        return {
            "status": "success",
            "query": query,
            "cached": False, # Managed by NewsService
            "articles": formatted_articles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
