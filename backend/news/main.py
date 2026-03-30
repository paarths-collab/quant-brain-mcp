import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from .service import NewsService
from .live_service import live_news_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["News"])

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
    limit: int = 12
):
    """
    Fetches real-time market headlines from DuckDuckGo News.
    """
    try:
        return live_news_service.get_news(query=query, limit=limit)
    except Exception as e:
        logger.exception("Live news failed")
        raise HTTPException(status_code=500, detail=str(e))

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
