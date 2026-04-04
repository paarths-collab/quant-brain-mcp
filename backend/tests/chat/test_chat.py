import pytest

@pytest.mark.asyncio
async def test_chat_status(client):
    """Test retrieved chat status."""
    response = await client.get("/api/chat/status")
    assert response.status_code == 200
    assert response.json()["status"] == "AI modules fully operational"
