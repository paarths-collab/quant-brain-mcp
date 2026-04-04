import pytest

@pytest.mark.asyncio
async def test_dashboard_sectors(client):
    """Test retrieving sector news for dashboard."""
    response = await client.get("/api/dashboard/sector-news")
    assert response.status_code == 200
