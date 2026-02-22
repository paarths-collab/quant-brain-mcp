"""
Market Pulse API — Sentiment analysis & sector news from PostgreSQL.

Routes:
  POST /api/market-pulse/sentiment   — emotion + DDG + Tavily news sentiment
  GET  /api/market-pulse/sector-news — sector-wise news from DB
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.database.connection import get_db
from backend.agents.emotion_agent import EmotionAnalysisAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market-pulse", tags=["Market Pulse"])

_EMOTION_AGENT = EmotionAnalysisAgent()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SentimentRequest(BaseModel):
    message: str = Field(..., description="User text to analyze for emotion")
    tickers: Optional[List[str]] = Field(default=None, description="Optional stock tickers")
    market: str = Field(default="us")


class NewsItem(BaseModel):
    title: str
    url: Optional[str] = None
    snippet: Optional[str] = None
    source: Optional[str] = None
    sentiment: Optional[str] = None  # positive / negative / neutral


class SentimentResponse(BaseModel):
    emotion: Dict[str, Any]      # from EmotionAgent
    news_sentiment: Dict[str, Any]  # aggregated headline sentiment
    tavily_insights: List[Dict[str, Any]]  # deep Tavily search results
    overall_mood: str             # bullish / bearish / neutral


# ---------------------------------------------------------------------------
# News helpers — DDG primary, Tavily 1-2x
# ---------------------------------------------------------------------------

def _fetch_ddg_news(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """Fetch news headlines from DuckDuckGo (primary, free)."""
    try:
        from backend.services.news_service import news_service
        
        # Use centralized news service
        results = news_service.get_news(query, max_results)
        
        items = []
        for r in results:
            items.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("body", ""),
                "source": r.get("source", "DDG"),
            })
        return items
    except Exception as e:
        logger.warning(f"DDG news failed: {e}")
        return []


def _fetch_tavily_deep(query: str, max_results: int = 2) -> List[Dict[str, Any]]:
    """Run 1-2 deep Tavily searches (limited usage)."""
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return []
        client = TavilyClient(api_key=api_key)
        result = client.search(query, max_results=max_results)
        items = []
        for r in result.get("results", []):
            items.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:300],
                "source": "Tavily",
                "score": r.get("score", 0),
            })
        return items
    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")
        return []


def _classify_headline_sentiment(headlines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Simple keyword-based headline sentiment classification."""
    positive_words = {
        "surge", "rally", "gain", "up", "rise", "soar", "bull", "growth",
        "record", "beat", "strong", "profit", "jumps", "boost", "high",
        "upgrade", "outperform", "buy", "positive", "optimistic",
    }
    negative_words = {
        "crash", "drop", "fall", "down", "loss", "bear", "decline", "fear",
        "risk", "sell", "warning", "miss", "weak", "low", "cut", "plunge",
        "downgrade", "underperform", "negative", "concern", "recession",
    }

    pos_count = 0
    neg_count = 0
    neu_count = 0
    classified: List[Dict[str, Any]] = []

    for item in headlines:
        text = (item.get("title", "") + " " + item.get("snippet", "")).lower()
        pos_hits = sum(1 for w in positive_words if w in text)
        neg_hits = sum(1 for w in negative_words if w in text)

        if pos_hits > neg_hits:
            sentiment = "positive"
            pos_count += 1
        elif neg_hits > pos_hits:
            sentiment = "negative"
            neg_count += 1
        else:
            sentiment = "neutral"
            neu_count += 1

        classified.append({**item, "sentiment": sentiment})

    total = max(pos_count + neg_count + neu_count, 1)
    return {
        "headlines": classified[:10],
        "positive_count": pos_count,
        "negative_count": neg_count,
        "neutral_count": neu_count,
        "positive_pct": round(pos_count / total * 100, 1),
        "negative_pct": round(neg_count / total * 100, 1),
        "neutral_pct": round(neu_count / total * 100, 1),
    }


def _compute_overall_mood(emotion: Dict[str, Any], news_sent: Dict[str, Any]) -> str:
    """Derive overall market mood from emotion + news signals."""
    # Check emotion intensity
    intensity = emotion.get("emotion_intensity", 0)
    label = emotion.get("emotion_label", "calm")

    # Check news sentiment balance
    pos_pct = news_sent.get("positive_pct", 0)
    neg_pct = news_sent.get("negative_pct", 0)

    # If user is highly emotional (panic/fomo), flag it
    if intensity > 0.6 and label in ("anxious", "excited", "highly_emotional"):
        return "⚠️ Emotional — Exercise Caution"
    if pos_pct > 60:
        return "🟢 Bullish"
    if neg_pct > 60:
        return "🔴 Bearish"
    return "⚖️ Neutral"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/sentiment")
def analyze_sentiment(request: SentimentRequest):
    """
    Full sentiment analysis:
    1. Emotion bias detection on user text
    2. DuckDuckGo news (primary, ~8 headlines)
    3. Tavily deep search (1-2 results)
    4. Headline sentiment classification
    5. Overall mood computation
    """
    try:
        # 1. Emotion analysis
        emotion = _EMOTION_AGENT.analyze(request.message)

        # 2. Build search query
        tickers_str = " ".join(request.tickers or [])
        search_query = f"{tickers_str} stock market news" if tickers_str else "stock market news"

        # 3. DDG news (primary)
        ddg_news = _fetch_ddg_news(search_query, max_results=8)

        # 4. Tavily deep search (1-2 results for enrichment)
        tavily_query = f"{tickers_str} investment analysis outlook" if tickers_str else "market outlook"
        tavily_insights = _fetch_tavily_deep(tavily_query, max_results=2)

        # 5. Combine and classify sentiment
        all_headlines = ddg_news + tavily_insights
        news_sentiment = _classify_headline_sentiment(all_headlines)

        # 6. Overall mood
        overall_mood = _compute_overall_mood(emotion, news_sentiment)

        return {
            "emotion": emotion,
            "news_sentiment": news_sentiment,
            "tavily_insights": tavily_insights,
            "overall_mood": overall_mood,
        }
    except Exception as e:
        logger.exception("Sentiment analysis failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sector-news")
def get_sector_news(
    market: str = Query("US"),
    sector: Optional[str] = Query(None),
    limit: int = Query(20),
    db=Depends(get_db),
):
    """
    Fetch sector-wise news from PostgreSQL sector_news_item table.
    Returns grouped by sector.
    """
    try:
        if sector:
            rows = db.execute(
                text("""
                    SELECT sector, title, url, source, snippet, published_at
                    FROM sector_news_item
                    WHERE UPPER(market) = :market AND LOWER(sector) = LOWER(:sector)
                    ORDER BY published_at DESC NULLS LAST
                    LIMIT :limit
                """),
                {"market": market.upper(), "sector": sector, "limit": limit},
            ).mappings().all()
        else:
            rows = db.execute(
                text("""
                    SELECT sector, title, url, source, snippet, published_at
                    FROM sector_news_item
                    WHERE UPPER(market) = :market
                    ORDER BY published_at DESC NULLS LAST
                    LIMIT :limit
                """),
                {"market": market.upper(), "limit": limit},
            ).mappings().all()

        # Group by sector
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            r = dict(row)
            sec = r.get("sector", "Unknown")
            if r.get("published_at"):
                r["published_at"] = r["published_at"].isoformat()
            if sec not in grouped:
                grouped[sec] = []
            grouped[sec].append(r)

        return {
            "market": market.upper(),
            "total_items": len(rows),
            "sectors": grouped,
        }
    except Exception as e:
        logger.exception("Sector news query failed")
        raise HTTPException(status_code=500, detail=str(e))
