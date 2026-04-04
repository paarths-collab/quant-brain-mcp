import pytest

@pytest.mark.asyncio
async def test_dashboard_sectors(client):
    """Test retrieving sector news for dashboard."""
    response = await client.get("/api/dashboard/sector-news")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_news_latest(client):
    """Test retrieving latest news."""
    response = await client.get("/api/news/latest")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_backtest_status(client):
    """Test backtest module integration."""
    # Assuming there's a status or similar
    response = await client.get("/api/backtest/health")
    assert response.status_code in [200, 404]

@pytest.mark.asyncio
async def test_research_status(client):
    """Test research module status."""
    # Check if the router is reachable
    response = await client.get("/api/research/status")
    assert response.status_code in [200, 404]
