from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.agents.emotion_agent import EmotionAnalysisAgent
from backend.services.data_loader import get_history, format_ticker
from backend.utils.sentiment import calculate_headline_sentiment

try:
    from backend.finverse_integration.utils.news_fetcher import NewsFetcher
except Exception:
    NewsFetcher = None

try:
    from backend.services.emotion_data_scraper import scrape_emotion_data
except Exception:
    scrape_emotion_data = None

try:
    from backend.services.cooldown_lock import get_cooldown_manager
except Exception:
    get_cooldown_manager = None


_EMOTION_AGENT = EmotionAnalysisAgent()
_NEWS_FETCHER = NewsFetcher() if NewsFetcher else None
_COOLDOWN_MANAGER = get_cooldown_manager() if get_cooldown_manager else None


@dataclass
class MarketContext:
    ticker: str
    metrics: Dict[str, Any]
    historical_context: Optional[str] = None


def analyze_emotion_safe_advice(
    message: str,
    tickers: Optional[List[str]] = None,
    market: str = "us",
    time_horizon_years: Optional[float] = None,
   risk_tolerance: Optional[str] = None,
    recent_action: Optional[str] = None,
    include_market_data: bool = True,
    include_news: bool = True,
    include_social_sentiment: bool = False,
    include_comprehensive_scrape: bool = False,
    user_id: Optional[str] = None,
    check_cooldown: bool = False,
    auto_create_cooldown: bool = False,
) -> Dict[str, Any]:
    """
    Core pipeline for the Emotion-Safe Investment Advisor.
    Detects emotional bias, optionally adds market context, and returns guidance.
    
    Args:
        include_social_sentiment: Include Reddit/social media sentiment
        include_comprehensive_scrape: Include full scrape (news, social, insider, analyst)
        user_id: Optional user identifier for cooldown tracking
        check_cooldown: Check if user has active cooldown lock
        auto_create_cooldown: Automatically create cooldown when high emotion detected
    """
    # Check for active cooldown lock
    cooldown_status = None
    if check_cooldown and user_id and _COOLDOWN_MANAGER:
        ticker_to_check = tickers[0] if tickers else None
        active_lock = _COOLDOWN_MANAGER.check_lock(user_id, ticker_to_check)
        if active_lock:
            remaining = _COOLDOWN_MANAGER.get_time_remaining(active_lock)
            cooldown_status = {
                "active": True,
                "reason": active_lock["reason"],
                "expires_at": active_lock["expires_at"],
                "time_remaining_hours": remaining.total_seconds() / 3600,
                "ticker": active_lock.get("ticker"),
                "created_at": active_lock["created_at"],
                "can_override": True,
            }
    
    bias_analysis = _EMOTION_AGENT.analyze(message)

    market_context: Dict[str, Any] = {}
    news_context: Dict[str, Any] = {}
    comprehensive_data: Dict[str, Any] = {}
    historical_notes: List[str] = []

    if include_market_data and tickers:
        for ticker in tickers:
            context = _build_market_context(ticker, market)
            market_context[context.ticker] = context.metrics
            if context.historical_context:
                historical_notes.append(context.historical_context)

    if include_news and tickers:
        for ticker in tickers:
            news_context[ticker] = _build_news_context(ticker)
    
    # Comprehensive scrape (news, social, insider, analyst)
    if include_comprehensive_scrape and tickers and scrape_emotion_data:
        for ticker in tickers:
            try:
                comprehensive_data[ticker] = scrape_emotion_data(ticker, market)
            except Exception as e:
                comprehensive_data[ticker] = {"error": str(e), "available": False}

    guidance = _build_guidance(
        bias_analysis=bias_analysis,
        market_context=market_context,
        news_context=news_context,
        time_horizon_years=time_horizon_years,
        risk_tolerance=risk_tolerance,
        recent_action=recent_action,
    )

    nudge = _build_nudge(bias_analysis, market_context)
    next_questions = _build_next_questions(message, tickers, time_horizon_years, risk_tolerance)
    
    # Build action recommendation
    action_recommendation = _build_action_recommendation(
        bias_analysis=bias_analysis,
        market_context=market_context,
        news_context=news_context,
        comprehensive_data=comprehensive_data,
    )
    
    # Auto-create cooldown lock if high emotion detected
    cooldown_created = None
    if auto_create_cooldown and user_id and _COOLDOWN_MANAGER:
        emotion_intensity = bias_analysis.get("emotion_intensity", 0)
        dominant_bias = bias_analysis.get("dominant_bias")
        
        should_lock = _COOLDOWN_MANAGER.should_trigger_cooldown(
            emotion_intensity=emotion_intensity,
            dominant_bias=dominant_bias,
            action_recommendation=action_recommendation,
        )
        
        if should_lock and not cooldown_status:  # Don't create if already locked
            ticker_to_lock = tickers[0] if tickers else None
            cooldown_created = _COOLDOWN_MANAGER.create_lock(
                user_id=user_id,
                ticker=ticker_to_lock,
                reason=f"High emotion detected: {dominant_bias} (intensity: {emotion_intensity:.2f})",
                duration_hours=24,
                metadata={
                    "message": message,
                    "emotion_intensity": emotion_intensity,
                    "dominant_bias": dominant_bias,
                    "action_recommendation": action_recommendation,
                },
            )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "message": message,
        "bias_analysis": bias_analysis,
        "market_context": market_context,
        "news_context": news_context,
        "comprehensive_data": comprehensive_data if comprehensive_data else None,
        "historical_context": historical_notes,
        "action_recommendation": action_recommendation,
        "cooldown_lock": {
            "status": cooldown_status,
            "created": cooldown_created,
            "feature_enabled": check_cooldown or auto_create_cooldown,
        },
        "guidance": guidance,
        "nudge": nudge,
        "next_questions": next_questions,
    }


def _build_market_context(ticker: str, market: str) -> MarketContext:
    end_date = pd.Timestamp.now().normalize()
    start_date = end_date - pd.DateOffset(years=5)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    formatted = format_ticker(ticker, market)

    try:
        df = get_history(formatted, start_str, end_str, market)
        if df.empty or "Close" not in df.columns:
            return MarketContext(
                ticker=formatted,
                metrics={"error": "No market data found"},
                historical_context=None,
            )
    except Exception as exc:
        return MarketContext(
            ticker=formatted,
            metrics={"error": str(exc)},
            historical_context=None,
        )

    close = df["Close"].dropna()
    returns = close.pct_change().dropna()

    vol_1y = _annualized_volatility(returns)
    vol_30d = _annualized_volatility(returns.tail(30)) if len(returns) >= 30 else vol_1y

    volatility_state = "normal"
    if vol_30d > vol_1y * 1.2:
        volatility_state = "elevated"
    elif vol_30d < vol_1y * 0.8:
        volatility_state = "subdued"

    drawdown = close / close.cummax() - 1
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0
    current_drawdown = float(drawdown.iloc[-1]) if not drawdown.empty else 0.0

    recovery_days = _estimate_recovery_days(close)

    recent_return_1m = _safe_return(close, 21)
    recent_return_6m = _safe_return(close, 126)

    historical_context = _format_historical_context(formatted, max_drawdown, recovery_days)

    metrics = {
        "last_price": round(float(close.iloc[-1]), 2),
        "volatility_30d_pct": round(vol_30d * 100, 2),
        "volatility_1y_pct": round(vol_1y * 100, 2),
        "volatility_state": volatility_state,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "current_drawdown_pct": round(current_drawdown * 100, 2),
        "return_1m_pct": round(recent_return_1m * 100, 2) if recent_return_1m is not None else None,
        "return_6m_pct": round(recent_return_6m * 100, 2) if recent_return_6m is not None else None,
        "period_start": start_str,
        "period_end": end_str,
    }

    return MarketContext(
        ticker=formatted,
        metrics=metrics,
        historical_context=historical_context,
    )


def _annualized_volatility(returns: pd.Series) -> float:
    if returns is None or returns.empty:
        return 0.0
    return float(returns.std()) * math.sqrt(252)


def _safe_return(close: pd.Series, window: int) -> Optional[float]:
    if close is None or close.empty or len(close) <= window:
        return None
    return float(close.iloc[-1] / close.iloc[-(window + 1)] - 1)


def _estimate_recovery_days(close: pd.Series) -> Optional[int]:
    if close is None or close.empty:
        return None

    drawdown = close / close.cummax() - 1
    if drawdown.empty:
        return None

    trough_idx = drawdown.idxmin()
    peak_value = close.cummax().loc[trough_idx]

    recovery_slice = close.loc[trough_idx:]
    recovery_candidates = recovery_slice[recovery_slice >= peak_value]
    if recovery_candidates.empty:
        return None

    recovery_idx = recovery_candidates.index[0]
    try:
        trough_pos = close.index.get_indexer([trough_idx])[0]
        recovery_pos = close.index.get_indexer([recovery_idx])[0]
        return int(recovery_pos - trough_pos)
    except Exception:
        return None


def _format_historical_context(
    ticker: str,
    max_drawdown: float,
    recovery_days: Optional[int],
) -> Optional[str]:
    if max_drawdown >= -0.05:
        return f"In the last 5 years, {ticker} saw shallow drawdowns (max {max_drawdown * 100:.1f}%)."

    if recovery_days is None:
        return (
            f"In the last 5 years, {ticker} saw a max drawdown of {max_drawdown * 100:.1f}% "
            "and has not fully recovered yet."
        )

    return (
        f"In the last 5 years, {ticker} saw a max drawdown of {max_drawdown * 100:.1f}% "
        f"and recovered in about {recovery_days} trading days."
    )


def _build_guidance(
    bias_analysis: Dict[str, Any],
    market_context: Dict[str, Any],
    news_context: Dict[str, Any],
    time_horizon_years: Optional[float],
    risk_tolerance: Optional[str],
    recent_action: Optional[str],
) -> List[Dict[str, str]]:
    guidance: List[Dict[str, str]] = []

    panic_score = _bias_score(bias_analysis, "panic_selling")
    fomo_score = _bias_score(bias_analysis, "fomo_buying")
    overconfidence_score = _bias_score(bias_analysis, "overconfidence")
    revenge_score = _bias_score(bias_analysis, "revenge_trading")

    if panic_score >= 0.3:
        guidance.append(
            {
                "title": "Pause the impulse",
                "message": "Your message shows panic cues. Consider a 24-hour pause and recheck your original plan before selling.",
            }
        )

    if fomo_score >= 0.3:
        guidance.append(
            {
                "title": "Avoid chasing",
                "message": "FOMO language detected. Consider scaling in over time or using limit orders instead of rushing in.",
            }
        )

    if overconfidence_score >= 0.3:
        guidance.append(
            {
                "title": "Size the position",
                "message": "Overconfidence cues detected. Set a max position size so one trade does not dominate your portfolio.",
            }
        )

    if revenge_score >= 0.3:
        guidance.append(
            {
                "title": "Reset the frame",
                "message": "Revenge-trading cues detected. Focus on process over recovery and avoid increasing risk to 'make it back.'",
            }
        )

    if recent_action and recent_action.lower() in {"buy", "sell"}:
        guidance.append(
            {
                "title": "Document the rationale",
                "message": "Write down why you want to "
                f"{recent_action.lower()} and what would change your mind. This reduces emotion-driven reversals.",
            }
        )

    if market_context:
        volatility_states = {ctx.get("volatility_state") for ctx in market_context.values() if isinstance(ctx, dict)}
        if "elevated" in volatility_states:
            guidance.append(
                {
                    "title": "Volatility is elevated",
                    "message": "Recent volatility is above the 1-year baseline. Consider smaller position sizes or staggered entries.",
                }
            )
        elif volatility_states and volatility_states.issubset({"normal", "subdued"}):
            guidance.append(
                {
                    "title": "Volatility looks normal",
                    "message": "Recent volatility is within typical ranges. This is a good time to review your long-term plan.",
                }
            )

    if news_context:
        for ticker, news in news_context.items():
            if not isinstance(news, dict):
                continue
            sentiment_label = news.get("sentiment_label")
            sentiment_score = news.get("sentiment_score")
            if sentiment_label == "negative" and sentiment_score is not None and sentiment_score <= -0.2:
                guidance.append(
                    {
                        "title": f"News tone is negative for {ticker}",
                        "message": "Recent headlines are skewing negative. Consider reviewing the thesis and risk exposure before adding more.",
                    }
                )
            elif sentiment_label == "positive" and fomo_score >= 0.3:
                guidance.append(
                    {
                        "title": f"Positive headlines for {ticker}",
                        "message": "Good news can intensify FOMO. If you still want exposure, consider smaller or staged entries.",
                    }
                )

    if time_horizon_years and time_horizon_years >= 5:
        guidance.append(
            {
                "title": "Anchor to horizon",
                "message": f"With a {time_horizon_years:.0f}-year horizon, short-term swings usually matter less than long-term allocation.",
            }
        )

    if risk_tolerance:
        guidance.append(
            {
                "title": "Align to risk tolerance",
                "message": f"Your stated risk tolerance is {risk_tolerance}. Make sure any trade fits that level of volatility.",
            }
        )

    if not guidance:
        guidance.append(
            {
                "title": "Stay process-driven",
                "message": "No strong emotional signals detected. Keep decisions anchored to goals, time horizon, and position sizing.",
            }
        )

    return guidance[:6]


def _build_nudge(bias_analysis: Dict[str, Any], market_context: Dict[str, Any]) -> str:
    if bias_analysis.get("emotion_intensity", 0) >= 0.6:
        return "Strong emotion cues detected. Consider slowing down and reviewing your plan before acting."

    volatility_states = {ctx.get("volatility_state") for ctx in market_context.values() if isinstance(ctx, dict)}
    if "elevated" in volatility_states:
        return "Volatility is elevated. A smaller, staged approach can reduce regret."

    if bias_analysis.get("emotion_intensity", 0) >= 0.3:
        return "Some emotion cues detected. A short pause can improve decision quality."

    return "Your message looks relatively calm. Focus on goals, diversification, and time horizon."


def _build_action_recommendation(
    bias_analysis: Dict[str, Any],
    market_context: Dict[str, Any],
    news_context: Dict[str, Any],
    comprehensive_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Returns a coarse action recommendation: HOLD, REVIEW, or CONSIDER_SELL.
    This is intentionally conservative and should not be treated as a trade signal.
    
    Enhanced with comprehensive data (social sentiment, insider activity, analyst actions)
    """
    emotion_intensity = float(bias_analysis.get("emotion_intensity", 0))
    dominant_bias = bias_analysis.get("dominant_bias")

    if emotion_intensity >= 0.7:
        return "REVIEW"

    if dominant_bias in {"panic_selling", "revenge_trading", "overconfidence"} and emotion_intensity >= 0.4:
        return "REVIEW"

    negative_news_hits = 0
    for news in news_context.values():
        if not isinstance(news, dict):
            continue
        if news.get("sentiment_label") == "negative" and (news.get("sentiment_score") or 0) <= -0.2:
            negative_news_hits += 1

    deep_drawdown = False
    for ctx in market_context.values():
        if not isinstance(ctx, dict):
            continue
        current_dd = ctx.get("current_drawdown_pct")
        if current_dd is not None and current_dd <= -20:
            deep_drawdown = True
    
    # Enhanced: Check comprehensive data if available
    bearish_signals = 0
    bullish_signals = 0
    
    if comprehensive_data:
        for ticker_data in comprehensive_data.values():
            if not isinstance(ticker_data, dict):
                continue
            
            # Check insider activity
            insider = ticker_data.get("insider_activity", {})
            if insider.get("net_signal") == "bearish" and insider.get("sells", 0) > insider.get("buys", 0) * 2:
                bearish_signals += 1
            elif insider.get("net_signal") == "bullish":
                bullish_signals += 1
            
            # Check analyst actions
            analyst = ticker_data.get("analyst_actions", {})
            if analyst.get("net_signal") == "bearish" and analyst.get("downgrades", 0) > analyst.get("upgrades", 0):
                bearish_signals += 1
            elif analyst.get("net_signal") == "bullish":
                bullish_signals += 1
            
            # Check social sentiment
            social = ticker_data.get("social_sentiment", {})
            if social.get("available") and social.get("avg_sentiment", 0) < -0.3:
                bearish_signals += 1
            elif social.get("avg_sentiment", 0) > 0.3:
                bullish_signals += 1
    
    # Strong bearish confluence
    if bearish_signals >= 2 and deep_drawdown:
        return "CONSIDER_SELL"

    if negative_news_hits >= 1 and deep_drawdown:
        return "CONSIDER_SELL"

    if negative_news_hits >= 1:
        return "REVIEW"

    return "HOLD"


def _build_news_context(ticker: str) -> Dict[str, Any]:
    """
    Fetch recent news and compute headline sentiment.
    Uses DDG fallback if Finnhub unavailable.
    Returns a safe structure even if news is unavailable.
    """
    if not _NEWS_FETCHER:
        # Fallback to DuckDuckGo directly
        try:
            from backend.services.news_service import news_service
            results = news_service.get_news(f"{ticker} stock", 6)
            headlines = [r.get("title", "") for r in results]
            score = calculate_headline_sentiment(headlines)
            sentiment_label = "neutral"
            if score >= 0.2:
                sentiment_label = "positive"
            elif score <= -0.2:
                sentiment_label = "negative"
            return {
                "available": True,
                "type": "market_sentiment",
                "scope": "market_sentiment",
                "source": "duckduckgo",
                "sentiment_score": round(float(score), 3),
                "sentiment_label": sentiment_label,
                "headlines": headlines[:5],
                "items": results[:5],
            }
        except Exception as e:
            return {"available": False, "reason": f"DDG fallback failed: {e}"}

    try:
        news_items = _NEWS_FETCHER.fetch_news(ticker, limit=6)
        headlines = [n.get("title", "") for n in news_items if isinstance(n, dict)]
        score = calculate_headline_sentiment(headlines)
        sentiment_label = "neutral"
        if score >= 0.2:
            sentiment_label = "positive"
        elif score <= -0.2:
            sentiment_label = "negative"

        scope = "company"
        if news_items and all(isinstance(n, dict) and n.get("source") == "DuckDuckGo" for n in news_items):
            scope = "market_sentiment"

        return {
            "available": True,
            "type": scope,
            "scope": scope,
            "sentiment_score": round(float(score), 3),
            "sentiment_label": sentiment_label,
            "headlines": headlines[:5],
            "items": news_items[:5],
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def _build_next_questions(
    message: str,
    tickers: Optional[List[str]],
    time_horizon_years: Optional[float],
    risk_tolerance: Optional[str],
) -> List[str]:
    questions: List[str] = []
    if not tickers:
        questions.append("Which ticker(s) are you considering?")
    if time_horizon_years is None:
        questions.append("What is your time horizon in years?")
    if not risk_tolerance:
        questions.append("What is your risk tolerance (low, medium, high)?")
    if not message or len(message.split()) < 6:
        questions.append("Can you share a bit more detail about your goal or concern?")
    return questions[:3]


def _bias_score(bias_analysis: Dict[str, Any], bias_name: str) -> float:
    for bias in bias_analysis.get("biases", []):
        if bias.get("bias") == bias_name:
            return float(bias.get("score", 0.0))
    return 0.0
