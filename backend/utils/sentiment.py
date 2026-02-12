from typing import List, Dict, Any, Union
import logging
import re

logger = logging.getLogger(__name__)

# Flag to explicitly disable NLTK (set to False to use keyword-based fallback)
USE_NLTK = False

# --- NLTK for VADER Sentiment (Local/Free) ---
# This provides a much more accurate sentiment score than simple keyword matching.
if USE_NLTK:
    try:
        import nltk
        from nltk.sentiment import SentimentIntensityAnalyzer
        # Check if the lexicon is already downloaded
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            print("Downloading VADER lexicon for sentiment analysis (one-time download)...")
            nltk.download("vader_lexicon")
        
        SIA = SentimentIntensityAnalyzer()
        _HAS_NLTK = True
    except Exception as e:
        logger.warning(f"NLTK VADER not available: {e}")
        _HAS_NLTK = False
        SIA = None
else:
    _HAS_NLTK = False
    SIA = None


def _keyword_sentiment(text: str) -> float:
    """
    Simple keyword-based sentiment analysis fallback.
    Returns a score between -1 and 1.
    """
    if not text:
        return 0.0
    
    text_lower = text.lower()
    
    # Positive keywords
    positive_keywords = [
        'upgrade', 'upgraded', 'growth', 'profit', 'surge', 'soar', 'rally', 'beat',
        'strong', 'bullish', 'positive', 'gain', 'increase', 'rise', 'up', 'success',
        'outperform', 'record', 'high', 'opportunity', 'buy', 'momentum', 'expansion'
    ]
    
    # Negative keywords
    negative_keywords = [
        'downgrade', 'downgraded', 'loss', 'losses', 'plunge', 'crash', 'drop', 'miss',
        'weak', 'bearish', 'negative', 'decline', 'decrease', 'fall', 'down', 'failure',
        'underperform', 'low', 'risk', 'sell', 'warning', 'concern', 'deficit', 'cut'
    ]
    
    positive_count = sum(1 for word in positive_keywords if word in text_lower)
    negative_count = sum(1 for word in negative_keywords if word in text_lower)
    
    total = positive_count + negative_count
    if total == 0:
        return 0.0
    
    # Normalize to -1 to 1 range
    score = (positive_count - negative_count) / max(total, 1)
    return max(-1.0, min(1.0, score))


def analyze_text_sentiment(text: Union[str, List[str]]) -> Dict[str, Any]:
    """
    Analyze sentiment of text and return comprehensive result.
    
    Args:
        text: Single text string or list of text strings
    
    Returns:
        Dict with 'score' (float -1 to 1) and 'label' (str: positive/negative/neutral)
    """
    if isinstance(text, list):
        if not text:
            return {"score": 0.0, "label": "neutral"}
        # Analyze each text and average
        scores = [analyze_text_sentiment(t)["score"] for t in text if isinstance(t, str)]
        avg_score = sum(scores) / len(scores) if scores else 0.0
    elif isinstance(text, str):
        if _HAS_NLTK and SIA:
            # Use VADER if available
            avg_score = SIA.polarity_scores(text)["compound"]
        else:
            # Use keyword-based fallback
            avg_score = _keyword_sentiment(text)
    else:
        return {"score": 0.0, "label": "neutral"}
    
    # Determine label
    if avg_score > 0.05:
        label = "positive"
    elif avg_score < -0.05:
        label = "negative"
    else:
        label = "neutral"
    
    return {
        "score": round(avg_score, 3),
        "label": label,
    }


def calculate_headline_sentiment(headlines: List[str]) -> float:
    """
    Calculates a single average compound sentiment score for a list of headlines.
    Returns a float between -1 (very negative) and 1 (very positive).
    
    This is the legacy function maintained for backward compatibility.
    For new code, use analyze_text_sentiment() instead.
    """
    if not headlines:
        return 0.0
    
    if _HAS_NLTK and SIA:
        compound_scores = []
        for h in headlines:
            if isinstance(h, str) and h.strip():
                compound_scores.append(SIA.polarity_scores(h)["compound"])
        return sum(compound_scores) / len(compound_scores) if compound_scores else 0.0
    else:
        # Use keyword-based fallback
        scores = [_keyword_sentiment(h) for h in headlines if isinstance(h, str) and h.strip()]
        return sum(scores) / len(scores) if scores else 0.0
