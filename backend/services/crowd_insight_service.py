from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from backend.agents.insider_agent import InsiderAgent
from backend.utils.sentiment import calculate_headline_sentiment

try:
    from backend.finverse_integration.utils.news_fetcher import NewsFetcher
except Exception:
    NewsFetcher = None


@dataclass
class SignalComponent:
    score: Optional[float]
    label: str
    available: bool
    details: Dict[str, Any]


def analyze_crowd_insight(
    ticker: str,
    market: str = "us",
    include_insider: bool = True,
    include_news: bool = True,
    finnhub_key: Optional[str] = None,
    rapidapi_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Crowd Insight Signal:
    - Insider activity (FMP roster + Finnhub transactions)
    - News sentiment (Finnhub headlines via NewsFetcher)
    """
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


def _build_insider_component(
    ticker: str,
    include_insider: bool,
    finnhub_key: Optional[str],
    rapidapi_config: Dict[str, Any],
) -> SignalComponent:
    if not include_insider:
        return SignalComponent(None, "unavailable", False, {"reason": "insider disabled"})

    if not finnhub_key or not rapidapi_config.get("key"):
        return SignalComponent(
            None,
            "unavailable",
            False,
            {"reason": "FINNHUB_API_KEY or RAPIDAPI_KEY missing"},
        )

    try:
        agent = InsiderAgent(finnhub_key=finnhub_key, rapidapi_config=rapidapi_config)
        results = agent.analyze(ticker)
        summary = results.get("summary", {}) if isinstance(results, dict) else {}
        buys = int(summary.get("Recent Buys (Count)", 0))
        sells = int(summary.get("Recent Sells (Count)", 0))
        score, label = _score_from_counts(buys, sells)
        return SignalComponent(
            score=score,
            label=label,
            available=True,
            details={
                "buys": buys,
                "sells": sells,
                "net_sentiment": summary.get("Net Sentiment", "Neutral"),
            },
        )
    except Exception as exc:
        return SignalComponent(None, "unavailable", False, {"reason": str(exc)})


def _build_news_component(ticker: str, include_news: bool) -> SignalComponent:
    if not include_news:
        return SignalComponent(None, "unavailable", False, {"reason": "news disabled"})

    if not NewsFetcher:
        return SignalComponent(None, "unavailable", False, {"reason": "NewsFetcher not available"})

    try:
        fetcher = NewsFetcher()
        items = fetcher.get_stock_news(ticker, limit=6, days_back=90)
        headlines = [item.get("title", "") for item in items if isinstance(item, dict)]
        score = calculate_headline_sentiment(headlines)
        label = _label_from_score(score)
        return SignalComponent(
            score=round(float(score), 3),
            label=label,
            available=True,
            details={
                "headlines": headlines[:5],
                "items": items[:5],
            },
        )
    except Exception as exc:
        return SignalComponent(None, "unavailable", False, {"reason": str(exc)})


def _score_from_counts(buys: int, sells: int) -> Tuple[float, str]:
    total = buys + sells
    if total == 0:
        return 0.0, "neutral"
    score = (buys - sells) / total
    return round(score, 3), _label_from_score(score)


def _label_from_score(score: float) -> str:
    if score >= 0.2:
        return "bullish"
    if score <= -0.2:
        return "bearish"
    return "neutral"


def _combine_components(
    insider_component: SignalComponent,
    news_component: SignalComponent,
) -> Tuple[float, str]:
    scores: Dict[str, float] = {}
    if insider_component.available and insider_component.score is not None:
        scores["insider"] = insider_component.score
    if news_component.available and news_component.score is not None:
        scores["news"] = news_component.score

    if not scores:
        return 0.0, "neutral"

    weights = {
        "insider": 0.6,
        "news": 0.4,
    }
    total_weight = sum(weights[key] for key in scores)
    combined = sum(scores[key] * weights[key] for key in scores) / total_weight
    combined = round(combined, 3)
    return combined, _label_from_score(combined)


def _estimate_confidence(
    insider_component: SignalComponent,
    news_component: SignalComponent,
) -> float:
    available = sum(
        1 for component in (insider_component, news_component) if component.available
    )
    if available == 0:
        return 0.2
    if available == 1:
        return 0.5
    return 0.7


def _component_payload(component: SignalComponent) -> Dict[str, Any]:
    return {
        "available": component.available,
        "label": component.label,
        "score": component.score,
        "details": component.details,
    }
