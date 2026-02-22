def calculate_confidence(financial_score: float, sentiment_score: float, sector_score: float, emotion_penalty: float) -> float:
    """
    Calculates a final confidence score (0-100) based on weighted inputs.
    
    Weights:
    - Financials: 40%
    - Sentiment (Web): 40% (Increased from 30% to normalize to 100)
    - Sector: 20%
    - Emotion Penalty: Subtracts directly (Risk management)
    """
    
    # Base calculation
    weighted_score = (
        0.4 * financial_score +
        0.4 * sentiment_score +
        0.2 * sector_score
    )
    
    # Apply emotion penalty (User anxiety reduces confidence in the *execution*, acting as a circuit breaker)
    # Actually, if the user is panicking, we might want high confidence in our answer to calm them, 
    # OR low confidence to suggest caution. 
    # The prompt says: "emotion_penalty" subtracts. Let's follow that logic (High anxiety = reduced system confidence to take aggressive action).
    
    final_confidence = weighted_score - (0.1 * emotion_penalty) # Small adjustment, or fully subtract penalty? 
    # User Code: 0.1 * emotion_penalty. 
    # If penalty is 15 (high anxiety), we subtract 1.5. That seems low. 
    # User Code: 
    # confidence = ( ... - 0.1 * emotion_penalty )
    # Let's stick to user's formula exactly.
    
    # Calculate final confidence using the correct weighted score
    final_confidence = weighted_score - (0.1 * emotion_penalty)

    return round(max(min(final_confidence, 100), 0), 2)
