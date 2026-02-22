from backend.agents.web_agent import WebAgent
import pytest

def test_web_agent():
    agent = WebAgent()
    # This test hits the LLM, so it requires GROQ_API_KEY
    result = agent.research("Latest news on NVIDIA")

    if "error" in result:
        pytest.fail(f"Web research failed: {result['error']}")

    assert "content" in result
    assert len(result["content"]) > 0
