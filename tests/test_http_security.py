"""Hosted authentication, ownership propagation, and admission regressions."""
import asyncio
import hashlib

import httpx
import pytest
from starlette.responses import JSONResponse

from core.http_security import SecureMCPMiddleware, authenticated_owner, load_api_keys

TOKEN_A = "a" * 40
TOKEN_B = "b" * 40
KEYS = {"alice": hashlib.sha256(TOKEN_A.encode()).hexdigest(),
        "bob": hashlib.sha256(TOKEN_B.encode()).hexdigest()}


async def endpoint(scope, receive, send):
    await JSONResponse({"owner": authenticated_owner.get()})(scope, receive, send)


def request(app, token=None, path="/mcp", **headers):
    async def run():
        if token:
            headers["authorization"] = "Bearer " + token
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post(path, headers=headers)
    return asyncio.run(run())


def test_auth_fails_closed_and_health_remains_available():
    app = SecureMCPMiddleware(endpoint, keys={})
    assert request(app).status_code == 503
    assert request(app, path="/health").status_code == 200


def test_invalid_tokens_rejected_and_spoofed_owner_ignored():
    app = SecureMCPMiddleware(endpoint, keys=KEYS)
    assert request(app).status_code == 401
    assert request(app, "wrong" * 8).status_code == 401
    assert request(app, TOKEN_A, **{"x-owner-id": "bob"}).json() == {"owner": "alice"}
    assert request(app, TOKEN_B).json() == {"owner": "bob"}
    assert authenticated_owner.get() is None


def test_origins_rejected_unless_explicitly_allowed(monkeypatch):
    app = SecureMCPMiddleware(endpoint, keys=KEYS)
    assert request(app, TOKEN_A, origin="https://untrusted.example").status_code == 403
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://trusted.example")
    assert request(app, TOKEN_A, origin="https://trusted.example").status_code == 200


def test_rate_limits_are_per_owner():
    app = SecureMCPMiddleware(endpoint, keys=KEYS, requests_per_minute=1)
    assert request(app, TOKEN_A).status_code == 200
    assert request(app, TOKEN_A).status_code == 429
    assert request(app, TOKEN_B).status_code == 200


def test_concurrent_requests_keep_owner_context_separate():
    async def run():
        seen = []
        async def slow(scope, receive, send):
            before = authenticated_owner.get()
            await asyncio.sleep(0.01)
            seen.append((before, authenticated_owner.get()))
            await endpoint(scope, receive, send)
        app = SecureMCPMiddleware(slow, keys=KEYS, max_inflight=2)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            results = await asyncio.gather(*(client.post('/mcp', headers={"authorization": "Bearer " + token})
                                             for token in [TOKEN_A, TOKEN_B, TOKEN_A]))
        assert sorted(r.status_code for r in results) == [200, 200, 429]
        assert set(seen) == {("alice", "alice"), ("bob", "bob")}
        assert app.inflight == 0
    asyncio.run(run())


def test_invalid_configuration_is_rejected(monkeypatch):
    monkeypatch.setenv("MCP_API_KEYS", '{"owner":"plaintext-secret"}')
    with pytest.raises(ValueError, match="SHA-256"):
        load_api_keys()


def test_alert_owner_not_exposed_in_mcp_schema():
    from fastmcp_server import mcp
    tool = next(t for t in asyncio.run(mcp.list_tools()) if t.name == "price_alert")
    assert "owner_id" not in tool.inputSchema["properties"]


def test_mcp_owner_context_reaches_alert_storage(monkeypatch):
    import fastmcp_server as server
    captured = []
    monkeypatch.setattr(server, "manage_alert", lambda *a, **kw: captured.append(kw["owner_id"]) or {"alerts": []})
    async def run():
        token = authenticated_owner.set("alice")
        try:
            await server.mcp.call_tool("price_alert", {"action": "list"})
        finally:
            authenticated_owner.reset(token)
    asyncio.run(run())
    assert captured == ["alice"]


def test_oversized_tool_workload_rejected_before_fetch(monkeypatch):
    import fastmcp_server as server
    monkeypatch.setattr(server, "run_get_quotes", lambda *a: pytest.fail("must not fetch"))
    with pytest.raises(Exception, match="at most 25"):
        asyncio.run(server.mcp.call_tool("get_quote", {"tickers": ["AAPL"] * 26}))


def test_body_limit_applies_to_chunked_requests():
    async def run():
        app = SecureMCPMiddleware(endpoint, keys=KEYS)
        async def chunks():
            yield b'x' * 600000
            yield b'x' * 600000
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            result = await client.post('/mcp', content=chunks(), headers={'authorization': 'Bearer ' + TOKEN_A})
        assert result.status_code == 413
    asyncio.run(run())


def test_cancelled_request_retains_worker_capacity(monkeypatch):
    import threading
    import fastmcp_server as server
    started, release = threading.Event(), threading.Event()
    monkeypatch.setattr(server, '_TOOL_SLOTS', threading.BoundedSemaphore(1))
    def slow(*args):
        started.set()
        release.wait(5)
        return {'quotes': {}}
    monkeypatch.setattr(server, 'run_get_quotes', slow)
    async def run():
        task = asyncio.create_task(server.mcp.call_tool('get_quote', {'tickers': ['AAPL']}))
        try:
            await asyncio.to_thread(started.wait, 2)
            assert started.is_set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            with pytest.raises(Exception, match='capacity reached'):
                await server.mcp.call_tool('get_quote', {'tickers': ['MSFT']})
        finally:
            release.set()
    asyncio.run(run())
