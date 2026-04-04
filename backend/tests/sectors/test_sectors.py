import pytest

@pytest.mark.asyncio
async def test_get_treemap_indices(client):
    """Test retrieving indices for the treemap."""
    response = await client.get("/api/treemap/indices?market=india")
    assert response.status_code == 200
    data = response.json()
    assert "indices" in data
    assert "market" in data
    assert data["market"] == "india"
