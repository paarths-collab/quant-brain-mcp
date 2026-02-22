from backend.engine.divergence_detector import detect_divergence

def test_divergence_detection():
    # Case 1: Strong Financials, Bearish News -> Divergence
    financial = {"score": 70}
    web = {"sentiment": "bearish", "score": 30}

    flags = detect_divergence(financial, web)
    assert len(flags) > 0
    assert "Financials are strong" in flags[0]

    # Case 2: Weak Financials, Bullish News -> Divergence
    financial_weak = {"score": 30}
    web_bull = {"sentiment": "bullish", "score": 70}
    
    flags2 = detect_divergence(financial_weak, web_bull)
    assert len(flags2) > 0
    assert "Financials are weak" in flags2[0]
    
    # Case 3: Alignment -> No Divergence
    financial_ok = {"score": 60}
    web_ok = {"sentiment": "bullish", "score": 65}
    flags3 = detect_divergence(financial_ok, web_ok)
    assert len(flags3) == 0
