import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from .service import NewsService
from .live_service import live_news_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["News"])

_NEWS_SERVICE = NewsService()

@router.get("/latest")
def get_latest_news(
    query: str = Query("stock market news"),
    limit: int = 10
):
    """
    Fetches latest news from GNews/DDG/Tavily.
    """
    try:
        return _NEWS_SERVICE.search_news(query=query)[:limit]
    except Exception as e:
        logger.exception("News fetch failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/live")
def get_live_news(
    query: str = Query("stock market"),
    limit: int = Query(12, ge=1, le=50),
    cached_only: bool = Query(False)
):
    """
    Fetches real-time market headlines from DuckDuckGo News.
    """
    try:
        if cached_only:
            return live_news_service.get_cached_news(query=query, limit=limit)
        return live_news_service.get_news(query=query, limit=limit)
    except Exception as e:
        logger.exception("Live news failed; returning cached fallback")
        try:
            return live_news_service.get_cached_news(query=query, limit=limit)
        except Exception:
            # Do not hard-fail the UI on upstream scrape/provider issues.
            return {
                "status": "success",
                "query": query,
                "cached": True,
                "stale": True,
                "articles": [],
                "source_count": 0,
                "message": f"Live news temporarily unavailable: {str(e)}",
            }

@router.get("/article-summary")
def get_article_summary(url: str = Query(...)):
    """
    Summarizes a news article URL using AI.
    """
    try:
        result = live_news_service.summarize_article(url=url)
        return result
    except Exception as e:
        logger.exception("Article summary failed")
        raise HTTPException(status_code=500, detail=str(e))
