"""
Chat sentiment adapter.

Delegates to the full sectors sentiment pipeline so chat/research endpoints
return rich fields (market_data, recommendation, news, supply_chain, etc.).
Falls back to a minimal shape only if the rich pipeline is unavailable.
"""
from typing import Dict, Any, List

try:
    from backend.sectors.core.stock_sentiment_service import (
        analyze_stock_sentiment as _rich_analyze_stock_sentiment,
        analyze_multiple_stocks as _rich_analyze_multiple_stocks,
    )
    _RICH_AVAILABLE = True
except Exception:
    _rich_analyze_stock_sentiment = None
    _rich_analyze_multiple_stocks = None
    _RICH_AVAILABLE = False


def _minimal_sentiment_shape(ticker: str) -> Dict[str, Any]:
    symbol = (ticker or "").upper().strip()
    return {
        "symbol": symbol,
        "ticker": symbol,
        "name": symbol,
        "score": 0.0,
        "label": "neutral",
        "confidence": 0.5,
        "source": "fallback",
        "sentiment": {"overall": 0.5, "summary": "Fallback sentiment response."},
        "recommendation": "HOLD",
        "outlook": "Neutral",
        "market_data": {},
        "news": {"articles": []},
        "supply_chain": {"customers": [], "suppliers": []},
    }


def get_sentiment_score(ticker: str) -> Dict[str, Any]:
    return analyze_stock_sentiment(ticker)


def get_stock_sentiment(ticker: str) -> Dict[str, Any]:
    return analyze_stock_sentiment(ticker)


def analyze_market_sentiment(tickers: List[str]) -> Dict[str, Any]:
    return {t: analyze_stock_sentiment(t) for t in tickers}


# Aliases used by chat pipeline
fetch_stock_sentiment = get_stock_sentiment
analyze_sentiment = get_stock_sentiment


# Aliases used by sentiment.py
def analyze_stock_sentiment(ticker: str):
    if _RICH_AVAILABLE and _rich_analyze_stock_sentiment is not None:
        try:
            return _rich_analyze_stock_sentiment(ticker)
        except Exception:
            return _minimal_sentiment_shape(ticker)
    return _minimal_sentiment_shape(ticker)


def analyze_multiple_stocks(tickers: list):
    if _RICH_AVAILABLE and _rich_analyze_multiple_stocks is not None:
        try:
            return _rich_analyze_multiple_stocks(tickers)
        except Exception:
            return [analyze_stock_sentiment(t) for t in tickers]
    return [analyze_stock_sentiment(t) for t in tickers]
