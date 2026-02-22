from backend.agents.web_agent import WebAgent
import pytest

def test_web_research():
    agent = WebAgent()
    # This invokes the full stack: DDG -> Tavily (if needed) -> LLM Sentiment
    result = agent.research("NVIDIA earnings news")

    assert "articles" in result
    assert "sentiment" in result
    assert "score" in result
    assert isinstance(result["score"], (int, float))
    
    # Check if articles were found (assuming internet access)
    # assert len(result["articles"]) > 0 
    # Commented out length check to avoid flaky tests if network is down/DDG blocks
