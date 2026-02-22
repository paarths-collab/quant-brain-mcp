import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

RUN_INTEGRATION = os.getenv("RUN_INTEGRATION_TESTS", "").strip().lower() in {"1", "true", "yes"}
pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Integration test (starts full pipeline + external calls). Set RUN_INTEGRATION_TESTS=1 to run.",
)

def test_websocket_endpoint():
    with client.websocket_connect("/ws/live") as websocket:
        # Send JSON request
        payload = {"query": "Analyze Tesla", "ticker": "TSLA"}
        websocket.send_json(payload)
        
        # Receive JSON response
        data = websocket.receive_json()
        
        assert "financial" in data
        assert data["financial"]["ticker"] == "TSLA"
        assert "risk_engine" in data
        assert "strategy" in data
        assert "report" in data
        
        print("WebSocket Response Keys:", data.keys())


def test_websocket_ticker_inference_from_query():
    """
    If the frontend only sends `query` (no explicit ticker), the backend should infer it
    and still return strategy + risk_engine for charts.
    """
    with client.websocket_connect("/ws/live") as websocket:
        websocket.send_json({"query": "analyze NVDA"})
        data = websocket.receive_json()

        assert "financial" in data
        assert data["financial"]["ticker"].upper().startswith("NVDA")
        assert "strategy" in data
        assert "risk_engine" in data
