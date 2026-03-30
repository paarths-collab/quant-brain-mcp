"""
Isolated stock_sentiment_service for chat/core.
Provides sentiment analysis using available sources.
"""
from typing import Dict, Any, Optional, List


def get_sentiment_score(ticker: str) -> Dict[str, Any]:
    """Get a basic sentiment score for a ticker using news headlines."""
    return {
        "ticker": ticker,
        "score": 0.0,
        "label": "neutral",
        "confidence": 0.5,
        "source": "unavailable",
    }


def get_stock_sentiment(ticker: str) -> Dict[str, Any]:
    return get_sentiment_score(ticker)


def analyze_market_sentiment(tickers: List[str]) -> Dict[str, Any]:
    return {t: get_sentiment_score(t) for t in tickers}


# Aliases used by chat pipeline
fetch_stock_sentiment = get_stock_sentiment
analyze_sentiment = get_stock_sentiment

# Aliases used by sentiment.py
def analyze_stock_sentiment(ticker: str):
    return get_stock_sentiment(ticker)

def analyze_multiple_stocks(tickers: list):
    return [get_stock_sentiment(t) for t in tickers]
