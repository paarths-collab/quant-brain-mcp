from typing import List
import logging

logger = logging.getLogger(__name__)

# --- NLTK for VADER Sentiment (Local/Free) ---
# This provides a much more accurate sentiment score than simple keyword matching.
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

def calculate_headline_sentiment(headlines: List[str]) -> float:
    """
    Calculates a single average compound sentiment score for a list of headlines
    using the robust VADER sentiment model.
    Returns a float between -1 (very negative) and 1 (very positive).
    """
    if not _HAS_NLTK or not SIA or not headlines:
        return 0.0
    
    compound_scores = []
    for h in headlines:
        if isinstance(h, str) and h.strip():
            # Get the polarity scores and use the 'compound' score
            compound_scores.append(SIA.polarity_scores(h)["compound"])
            
    return sum(compound_scores) / len(compound_scores) if compound_scores else 0.0
