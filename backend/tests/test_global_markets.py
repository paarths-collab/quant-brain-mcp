from backend.agents.super_agent import SuperAgent
import asyncio
import pytest

@pytest.mark.asyncio
async def test_super_agent_india():
    agent = SuperAgent()
    # Test Indian stock (Reliance)
    # Note: This requires network access to yfinance
    result = await agent.run("Analyze Reliance Industries", "RELIANCE", market="india")

    assert "financial" in result
    # Check if ticker was normalized
    assert result["financial"]["ticker"] == "RELIANCE.NS"
    assert "sector" in result
    # Check if sector agent used correct benchmark (conceptually, though we can't easily check internal var without mocking)
    assert result["sector"]["sector_etf"] == "^NSEI" or result["sector"]["sector_etf"] == "SMH" # fallback logic check if I missed something, but it should be ^NSEI
    assert result["sector"]["sector_etf"] == "^NSEI"

@pytest.mark.asyncio
async def test_super_agent_us():
    agent = SuperAgent()
    result = await agent.run("Analyze Apple", "AAPL", market="us")
    assert result["financial"]["ticker"] == "AAPL"
    assert "SMH" in str(result["sector"]) or "sector_etf" in result["sector"]
