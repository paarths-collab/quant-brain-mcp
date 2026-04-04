import pytest

@pytest.mark.asyncio
async def test_backtest_strategies(client):
    """Test retrieving available backtest strategies."""
    response = await client.get("/api/backtest/strategies")
    assert response.status_code == 200
    assert "strategies" in response.json()
