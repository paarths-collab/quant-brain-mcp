from backend.engine.confidence_engine import calculate_confidence

def test_confidence_calculation():
    # Standard case
    score = calculate_confidence(
        financial_score=70, 
        sentiment_score=60, 
        sector_score=65, 
        emotion_penalty=0
    )
    # Calculation with new weights (0.4/0.4/0.2): 
    # (0.4*70) + (0.4*60) + (0.2*65) - 0 = 28 + 24 + 13 = 65
    assert score == 65.0

    # With Penalty
    score_penalty = calculate_confidence(70, 60, 65, 20)
    # 65 - (0.1 * 20) = 63
    assert score_penalty == 63.0

    # Boundary checks
    score_high = calculate_confidence(120, 100, 100, 0) # Should cap at 100
    assert score_high == 100.0
    
    score_low = calculate_confidence(0, 0, 0, 100) # Should floor at 0
    assert score_low == 0.0
