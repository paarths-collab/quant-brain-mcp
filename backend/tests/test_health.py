import pytest

@pytest.mark.asyncio
async def test_main_health(client):
    """Test retrieving health status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
