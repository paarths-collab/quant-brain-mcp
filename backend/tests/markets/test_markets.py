import pytest

@pytest.mark.asyncio
async def test_market_overview(client):
    """Test retrieving market overview data."""
    response = await client.get("/api/markets/overview")
    assert response.status_code == 200
    data = response.json()
    assert "indices" in data
