import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from .core.emotion_agent import EmotionAnalysisAgent
from .core.insider_agent import InsiderAgent
from .core.sentiment_utils import calculate_headline_sentiment

try:
    from .core.news_fetcher import NewsFetcher
except ImportError:
    NewsFetcher = None

logger = logging.getLogger(__name__)
_EMOTION_AGENT = EmotionAnalysisAgent()

@dataclass
class SignalComponent:
    score: Optional[float]
    label: str
    available: bool
    details: Dict[str, Any]

def get_market_sentiment(message: str, tickers: Optional[List[str]] = None, market: str = "us") -> Dict[str, Any]:
    """
    Analyzes sentiment for a message and specific tickers for the dashboard.
    """
    analysis = _EMOTION_AGENT.analyze(message)
    return {
        "text": message,
        "market": market,
        "sentiment": analysis.get("sentiment", "Neutral"),
        "confidence": analysis.get("confidence", 0.5),
        "emotion": analysis.get("dominant_emotion", "Neutral"),
        "tickers": tickers or []
    }

def analyze_crowd_insight(
    ticker: str,
    market: str = "us",
    include_insider: bool = True,
    include_news: bool = True,
    finnhub_key: Optional[str] = None,
    rapidapi_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ticker = ticker.upper().strip()

    insider_component = _build_insider_component(
        ticker=ticker,
        include_insider=include_insider,
        finnhub_key=finnhub_key,
        rapidapi_config=rapidapi_config or {},
    )

    news_component = _build_news_component(
        ticker=ticker,
        include_news=include_news,
    )

    combined_score, combined_label = _combine_components(
        insider_component=insider_component,
        news_component=news_component,
    )

    confidence = _estimate_confidence(insider_component, news_component)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "ticker": ticker,
        "market": market.lower(),
        "components": {
            "insider": _component_payload(insider_component),
            "news": _component_payload(news_component),
        },
        "signal": {
            "score": combined_score,
            "label": combined_label,
            "confidence": confidence,
        },
    }

def _build_insider_component(ticker: str, include_insider: bool, finnhub_key: Optional[str], rapidapi_config: Dict[str, Any]) -> SignalComponent:
    if not include_insider or not finnhub_key:
        return SignalComponent(None, "unavailable", False, {"reason": "insider disabled or keys missing"})
    try:
        agent = InsiderAgent(finnhub_key=finnhub_key, rapidapi_config=rapidapi_config)
        results = agent.analyze(ticker)
        summary = results.get("summary", {})
        buys = summary.get("Recent Buys (Count)", 0)
        sells = summary.get("Recent Sells (Count)", 0)
        score = (float(buys) - float(sells)) / (float(buys) + float(sells)) if (buys + sells) > 0 else 0
        return SignalComponent(score, _label_from_score(score), True, {"buys": buys, "sells": sells})
    except Exception as e:
        return SignalComponent(None, "error", False, {"reason": str(e)})

def _build_news_component(ticker: str, include_news: bool) -> SignalComponent:
    if not include_news or not NewsFetcher:
        return SignalComponent(None, "unavailable", False, {"reason": "news disabled or fetcher missing"})
    try:
        fetcher = NewsFetcher()
        items = fetcher.get_stock_news(ticker, limit=6)
        headlines = [t.get("title", "") for t in items]
        score = calculate_headline_sentiment(headlines)
        return SignalComponent(score, _label_from_score(score), True, {"headlines": headlines[:3]})
    except Exception as e:
        return SignalComponent(None, "error", False, {"reason": str(e)})

def _label_from_score(score: float) -> str:
    if score >= 0.2: return "bullish"
    if score <= -0.2: return "bearish"
    return "neutral"

def _combine_components(insider_component: SignalComponent, news_component: SignalComponent) -> Tuple[float, str]:
    scores = []
    if insider_component.available: scores.append(insider_component.score)
    if news_component.available: scores.append(news_component.score)
    avg = sum(scores) / len(scores) if scores else 0
    return round(avg, 3), _label_from_score(avg)

def _estimate_confidence(insider_component: SignalComponent, news_component: SignalComponent) -> float:
    return 0.7 if insider_component.available and news_component.available else 0.4

def _component_payload(component: SignalComponent) -> Dict[str, Any]:
    return {"available": component.available, "label": component.label, "score": component.score, "details": component.details}
