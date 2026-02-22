from backend.agents.analyst_agent import AnalystAgent
import pytest

def test_financial_analysis():
    agent = AnalystAgent()
    # Mocking would be better here for CI/CD, but for now we test live or assume network access
    # Ideally we should mock MarketDataService
    
    result = agent.analyze("AAPL")

    if "error" in result:
        pytest.fail(f"Analysis failed: {result['error']}")

    assert "technicals" in result
    assert "fundamentals" in result
    assert "rsi" in result["technicals"]
