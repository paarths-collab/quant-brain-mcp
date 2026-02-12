import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.main import app
from backend.agents.emotion_agent import EmotionAnalysisAgent
from backend.services.emotion_advisor_service import analyze_emotion_safe_advice


def test_panic_bias_detection():
    agent = EmotionAnalysisAgent()
    result = agent.analyze("I'm panicking and want to sell everything now!")

    assert result["emotion_intensity"] >= 0.2
    assert any(bias["bias"] == "panic_selling" for bias in result["biases"])


def test_fomo_bias_detection():
    agent = EmotionAnalysisAgent()
    result = agent.analyze("This stock is going to the moon, I need to buy now!")

    assert result["emotion_intensity"] >= 0.2
    assert any(bias["bias"] == "fomo_buying" for bias in result["biases"])


def test_emotion_advisor_service_without_market_data():
    result = analyze_emotion_safe_advice(
        message="I'm scared and want to sell before it gets worse.",
        tickers=None,
        include_market_data=False,
        include_news=False,
    )

    assert "bias_analysis" in result
    assert "action_recommendation" in result
    assert "guidance" in result
    assert result["market_context"] == {}


def test_emotion_advisor_api():
    client = TestClient(app)
    response = client.post(
        "/api/emotion-advisor/analyze",
        json={
            "message": "I'm afraid I should sell everything.",
            "include_market_data": False,
            "include_news": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "bias_analysis" in data
    assert "action_recommendation" in data
    assert "guidance" in data
