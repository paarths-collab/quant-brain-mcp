import asyncio
from backend.engine.pipeline import InvestmentPipeline
import pytest

def test_full_pipeline_execution():
    pipeline = InvestmentPipeline()

    async def run_test():
        # Simulate a full user request
        return await pipeline.run(
            query="Analyze Apple and tell me if I should sell",
            ticker="AAPL",
            portfolio={"AAPL": 0.6, "MSFT": 0.4},
            session_id="test_session_1"
        )
    
    result = asyncio.run(run_test())

    # Verify Strict Contract Keys
    assert "emotion" in result
    assert "financial" in result
    assert "web" in result
    assert "sector" in result
    assert "macro" in result
    assert "insider" in result
    assert "risk" in result
    assert "divergence" in result
    assert "confidence" in result
    assert "report" in result

    # Verify Data Integrity
    assert isinstance(result["confidence"], float)
    assert isinstance(result["divergence"], list)
    assert "market_bias" in result["macro"]
    assert "risk_score" in result["risk"]

def test_pipeline_discovery_mode():
    pipeline = InvestmentPipeline()
    
    async def run_discovery():
        # Simulate Discovery request
        return await pipeline.run(
            query="Find me top AI stocks",
            session_id="test_discovery_1"
        )

    result = asyncio.run(run_discovery())
    
    assert "discovery" in result
    assert isinstance(result["discovery"], list)
