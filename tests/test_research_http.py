"""Real MCP JSON-RPC over authenticated ASGI; model execution is deterministic fake."""
import hashlib
import json
import threading
import time

from starlette.testclient import TestClient

from core.http_security import SecureMCPMiddleware
from core.research_service import ResearchLifecycle, ResearchService
from core.research_store import ResearchStore
from tests.research_fakes import FakeMarketData


class FakeRuntime:
    def __init__(self, calls):
        self.calls = calls

    async def run(self, role, prompt):
        self.calls.append(role)
        # No sources available: honest insufficient-evidence report exercises the
        # complete pipeline without asserting live model or market-data success.
        return {"summary": "No verified external sources in this deterministic test", "outcome": "insufficient_evidence"}


def test_research_over_authenticated_mcp_http(tmp_path, monkeypatch, request):
    import fastmcp_server as server
    from core import research_service

    calls = []
    service = ResearchService(ResearchStore(tmp_path / "research.sqlite3"), runtime_factory=lambda: FakeRuntime(calls),
                              instrument_resolver=FakeMarketData())
    request.addfinalizer(service.close)
    monkeypatch.setenv("QUANT_RESEARCH_ENABLED", "1")
    monkeypatch.setenv("QUANT_RESEARCH_DB", str(tmp_path / "research.sqlite3"))
    monkeypatch.setattr(research_service, "_service", service)
    # Session managers are single-use; restore the original global on teardown.
    monkeypatch.setattr(server.mcp, "_session_manager", None)
    tokens = {"alice": "a" * 40, "bob": "b" * 40}
    keys = {owner: hashlib.sha256(token.encode()).hexdigest() for owner, token in tokens.items()}
    app = ResearchLifecycle(SecureMCPMiddleware(server.mcp.streamable_http_app(), keys=keys, requests_per_minute=200))
    request_id = 0

    with TestClient(app) as client:
        def rpc(method, params, owner="alice"):
            nonlocal request_id
            request_id += 1
            response = client.post("/mcp", headers={
                "Authorization": "Bearer " + tokens[owner],
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-03-26",
            }, json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            assert response.status_code == 200, response.text
            if response.headers.get("content-type", "").startswith("text/event-stream"):
                payload = next(json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: "))
            else:
                payload = response.json()
            assert "error" not in payload, payload
            return payload["result"]

        def tool(name, arguments, owner="alice"):
            result = rpc("tools/call", {"name": name, "arguments": arguments}, owner)
            assert not result.get("isError"), result
            if "structuredContent" in result:
                return result["structuredContent"]
            return json.loads(next(item["text"] for item in result["content"] if item["type"] == "text"))

        assert client.post("/mcp", json={}).status_code == 401
        initialized = rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "research-http-test", "version": "1"}})
        assert "serverInfo" in initialized
        notified = client.post("/mcp", headers={"Authorization": "Bearer " + tokens["alice"], "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-03-26"}, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        assert notified.status_code == 202
        job = tool("start_research", {"question": "Investigate this NSE stock", "tickers": ["TCS"], "depth": "quick"})
        assert "id" in job, job
        job_id = job["id"]
        for name in ("get_research_status", "get_research_report", "cancel_research"):
            assert tool(name, {"job_id": job_id}, owner="bob") == {"error": "Research job not found"}
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status = tool("get_research_status", {"job_id": job_id})
            if status.get("status") in ("completed", "failed", "cancelled"):
                break
            threading.Event().wait(0.02)
        assert status["status"] == "completed", status
        report = tool("get_research_report", {"job_id": job_id})
        assert report["report"]["invocation_count"] == 4
        assert report["report"]["tickers"] == ["TCS.NS"]
        assert report["report"]["outcome"] == "insufficient_evidence"
        assert sorted(calls) == ["auditor", "company", "quant", "synthesizer"]
        assert len(report["events"]) == 8
        assert research_service._service is service
        assert not service._closing
    assert research_service._service is None
    assert service._closing
    assert service._executor is None
    service.close()
