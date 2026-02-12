from fastapi import APIRouter, HTTPException, Query
from backend.services.social_service import fetch_reddit_posts
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json

router = APIRouter(prefix="/api/social", tags=["Social Media"])


def _ddg_news(ddgs: Any, query: str, max_results: int) -> List[Dict[str, Any]]:
    try:
        return list(ddgs.news(keywords=query, max_results=max_results))
    except TypeError:
        return list(ddgs.news(query=query, max_results=max_results))

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
        ddgs_cls = None
        try:
            from ddgs import DDGS as DDGSClass
            ddgs_cls = DDGSClass
        except Exception:
            try:
                from duckduckgo_search import DDGS as DDGSClass
                ddgs_cls = DDGSClass
            except Exception:
                ddgs_cls = None

        if ddgs_cls is None:
            return {"status": "error", "message": "DuckDuckGo search not available", "articles": []}

        cache_dir = Path(__file__).resolve().parents[1] / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = hashlib.sha256(query.lower().encode("utf-8")).hexdigest()[:16]
        cache_path = cache_dir / f"news_{cache_key}.json"

        if cache_path.exists():
            try:
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
                cached_at = payload.get("cached_at")
                if cached_at:
                    cached_dt = datetime.fromisoformat(cached_at)
                    if datetime.utcnow() - cached_dt < timedelta(hours=max_age_hours):
                        return {
                            "status": "success",
                            "query": query,
                            "cached": True,
                            "cached_at": cached_at,
                            "articles": payload.get("articles", [])
                        }
            except Exception:
                pass

        articles: List[Dict[str, Any]] = []
        with ddgs_cls() as ddgs:
            for item in _ddg_news(ddgs, query, limit):
                articles.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "date": item.get("date"),
                    "summary": item.get("body"),
                })

        cache_path.write_text(
            json.dumps({
                "cached_at": datetime.utcnow().isoformat(),
                "articles": articles
            }),
            encoding="utf-8"
        )

        return {
            "status": "success",
            "query": query,
            "cached": False,
            "articles": articles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
