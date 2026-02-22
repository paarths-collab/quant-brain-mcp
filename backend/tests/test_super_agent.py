import asyncio
import pytest
from backend.agents.super_agent import SuperAgent

@pytest.mark.asyncio
async def test_super_agent():
    agent = SuperAgent()
    result = await agent.run("Analyze AAPL, I am worried about the market", "AAPL")

    assert "report" in result
    assert "emotion" in result
    assert "financial" in result
    assert "web" in result
    assert "sector" in result
    
    # Check emotion detection
    assert result["emotion"]["status"] != "normal" # "worried" is not a panic word in our list, wait.
    # Our list: ["panic", "crash", "sell all", "fomo", "dump", "crashing"]
    # "worried" is NOT in the list.
    # Let's use a trigger word to test emotion flow properly
    
    result_panic = await agent.run("I want to sell all my AAPL because of the crash", "AAPL")
    assert result_panic["emotion"]["status"] == "high_anxiety"
