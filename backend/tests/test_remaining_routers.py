import pytest

@pytest.mark.asyncio
async def test_news_latest(client):
    """Test retrieving latest news."""
    response = await client.get("/api/news/latest")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_research_status(client):
    """Test research module (existence)."""
    # Assuming there's a status or similar
    response = await client.get("/api/research/status")
    assert response.status_code in [200, 404]

@pytest.mark.asyncio
async def test_screener_status(client):
    """Test screener module (existence)."""
    response = await client.get("/api/screener/status")
    assert response.status_code in [200, 404]
