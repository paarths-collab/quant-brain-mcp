import pytest

@pytest.mark.asyncio
async def test_portfolio_overview(client):
    """Test retrieving portfolio overview."""
    response = await client.get("/api/portfolio/overview")
    assert response.status_code == 200
    assert "status" in response.json()
