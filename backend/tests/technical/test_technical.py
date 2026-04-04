import pytest

@pytest.mark.asyncio
async def test_get_strategies(client):
    """Test retrieving technical analysis strategies."""
    response = await client.get("/api/technical/strategies")
    assert response.status_code == 200
    assert "strategies" in response.json()
