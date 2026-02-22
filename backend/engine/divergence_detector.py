def detect_divergence(financial: dict, web: dict) -> list:
    """
    Detects divergence between financial data (technicals/fundamentals) and web sentiment.
    Returns a list of warning flags.
    """
    flags = []

    financial_score = financial.get("score", 0)
    sentiment = web.get("sentiment", "neutral")
    sentiment_score = web.get("score", 50)

    # 1. Bearish Divergence: Strong Financials vs Bearish News
    if financial_score > 60 and sentiment == "bearish":
        flags.append("Warning: Financials are strong (Score: >60), but Market Sentiment is Bearish.")

    # 2. Bullish Divergence: Weak Financials vs Bullish News
    if financial_score < 40 and sentiment == "bullish":
        flags.append("Warning: Financials are weak (Score: <40), but Market Sentiment is Bullish (Possible Hype/FOMO).")

    # 3. Extreme SENTIMENT divergence detection
    if abs(financial_score - sentiment_score) > 40:
        flags.append(f"Significant Divergence: Financial Score ({financial_score}) vs Sentiment Score ({sentiment_score}).")

    return flags
