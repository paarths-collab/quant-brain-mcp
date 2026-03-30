"""
Graceful news_service stub for sectors/core.
The sectors module has its own sentiment analysis pipeline.
News fetching for sector context is handled via the dedicated news module.
This stub satisfies the import without crashing.
"""
from typing import List, Dict, Any


class NewsService:
    """Minimal news service stub for sector context lookups."""

    def get_news(self, query: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        """Return an empty list — news module handles real fetching."""
        return []

    def search_news(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        return []


# Singleton-style object used by stock_sentiment_service
news_service = NewsService()
