from backend.agents.sector_agent import SectorAgent
import pytest

def test_sector():
    agent = SectorAgent()
    result = agent.analyze("SMH") # Semiconductor ETF

    if "error" in result:
        pytest.fail(f"Sector analysis failed: {result['error']}")

    assert "momentum" in result
    assert "score" in result
    assert isinstance(result["momentum"], float)
