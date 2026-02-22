from backend.agents.emotion_agent import EmotionAgent

def test_emotion_detection():
    agent = EmotionAgent()
    result = agent.evaluate("Sell everything, market crash!")

    assert result["status"] == "high_anxiety"
    assert "crash" in result["keywords"]

def test_emotion_normal():
    agent = EmotionAgent()
    result = agent.evaluate("Analyze AAPL please")
    
    assert result["status"] == "normal"
    assert result["penalty"] == 0
