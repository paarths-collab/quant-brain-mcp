"""Trusted MCP listeners and parallel calls have independent, bounded budgets."""
import asyncio
import hashlib

import httpx
import pytest
from starlette.responses import JSONResponse

from core.http_security import SecureMCPMiddleware

TOKEN = "internal-test-token-" + "a" * 32
HEADERS = {"Authorization": "Bearer " + TOKEN}
KEYS = {"internal-research": hashlib.sha256(TOKEN.encode()).hexdigest()}


def test_internal_streams_do_not_starve_parallel_tools_and_queue_drains():
    async def run():
        streams_started = asyncio.Event()
        release_streams = asyncio.Event()
        calls_started = asyncio.Event()
        release_calls = asyncio.Event()
        active = {"GET": 0, "POST": 0}
        peaks = dict(active)
        async def endpoint(scope, receive, send):
            method = scope["method"]
            active[method] += 1
            peaks[method] = max(peaks[method], active[method])
            try:
                if method == "GET":
                    if active[method] == 2:
                        streams_started.set()
                    await release_streams.wait()
                else:
                    if active[method] == 2:
                        calls_started.set()
                    await release_calls.wait()
                await JSONResponse({"ok": True})(scope, receive, send)
            finally:
                active[method] -= 1
        app = SecureMCPMiddleware(endpoint, keys=KEYS, max_inflight=2,
                                  max_streams=2, max_waiting=2, wait_seconds=1)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test", headers=HEADERS) as client:
            streams = [asyncio.create_task(client.get("/mcp")) for _ in range(2)]
            await asyncio.wait_for(streams_started.wait(), 1)
            denied_stream = await client.get("/mcp")
            assert denied_stream.status_code == 429
            calls = [asyncio.create_task(client.post("/mcp")) for _ in range(4)]
            await asyncio.wait_for(calls_started.wait(), 1)
            # Let all four requests enter the middleware before checking overflow.
            for _ in range(20):
                if app._calls.waiting == 2:
                    break
                await asyncio.sleep(0)
            assert app._calls.waiting == 2
            denied_call = await client.post("/mcp")
            assert denied_call.status_code == 429
            assert denied_call.headers["Retry-After"] == "1"
            assert "Concurrent" in denied_call.json()["error"]
            release_calls.set()
            assert all(r.status_code == 200 for r in await asyncio.gather(*calls))
            assert app._streams.active == 2
            release_streams.set()
            assert all(r.status_code == 200 for r in await asyncio.gather(*streams))
            assert peaks == {"GET": 2, "POST": 2}
            assert app.inflight == 0
            assert app._calls.waiting == 0
    asyncio.run(run())


def test_cancelled_and_timed_out_waiters_release_capacity():
    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        async def endpoint(scope, receive, send):
            started.set()
            await release.wait()
            await JSONResponse({"ok": True})(scope, receive, send)
        app = SecureMCPMiddleware(endpoint, keys=KEYS, max_inflight=1,
                                  max_waiting=1, wait_seconds=0.02)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test", headers=HEADERS) as client:
            first = asyncio.create_task(client.post("/mcp"))
            await asyncio.wait_for(started.wait(), 1)
            waiting = asyncio.create_task(client.post("/mcp"))
            while app._calls.waiting == 0:
                await asyncio.sleep(0)
            waiting.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiting
            assert app._calls.waiting == 0
            timed_out = await client.post("/mcp")
            assert timed_out.status_code == 429
            assert app._calls.waiting == 0
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            assert app.inflight == 0
            release.set()
            assert (await client.post("/mcp")).status_code == 200
    asyncio.run(run())


def test_admission_queue_does_not_bypass_rate_limit():
    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        async def endpoint(scope, receive, send):
            started.set()
            await release.wait()
            await JSONResponse({"ok": True})(scope, receive, send)
        app = SecureMCPMiddleware(endpoint, keys=KEYS, requests_per_minute=1,
                                  max_inflight=1, max_waiting=2, wait_seconds=1)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test", headers=HEADERS) as client:
            first = asyncio.create_task(client.post("/mcp"))
            await asyncio.wait_for(started.wait(), 1)
            denied = await client.post("/mcp")
            assert denied.status_code == 429
            assert "rate limit" in denied.json()["error"]
            assert 1 <= int(denied.headers["Retry-After"]) <= 60
            release.set()
            assert (await first).status_code == 200
    asyncio.run(run())
