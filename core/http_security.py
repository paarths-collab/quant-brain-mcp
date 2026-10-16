"""Bearer authentication and bounded HTTP admission for hosted MCP.

MCP_API_KEYS maps stable owner IDs to SHA-256 digests of random API tokens.
No identity supplied in a tool argument or an unverified header is trusted.
"""
from __future__ import annotations

from collections import defaultdict, deque
from contextvars import ContextVar
import asyncio
import hashlib
import json
import os
import re
import secrets
import time

from starlette.responses import JSONResponse

authenticated_owner: ContextVar[str | None] = ContextVar("authenticated_owner", default=None)


def load_api_keys() -> dict[str, str]:
    raw = os.getenv("MCP_API_KEYS", "")
    if not raw:
        return {}
    try:
        keys = json.loads(raw)
        if not isinstance(keys, dict) or not keys:
            raise ValueError
        if any(not isinstance(owner, str) or not owner.strip() or len(owner) > 128
               or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
               for owner, digest in keys.items()):
            raise ValueError
        if len(set(keys.values())) != len(keys):
            raise ValueError
        return keys
    except (ValueError, TypeError):
        raise ValueError("MCP_API_KEYS must map unique owner IDs to unique lowercase SHA-256 token digests") from None


class SecureMCPMiddleware:
    """Fail closed if unconfigured. Limits are per process, not distributed."""

    def __init__(self, app, *, keys=None, requests_per_minute=60, max_inflight=4):
        self.app = app
        self.keys = load_api_keys() if keys is None else keys
        self.requests_per_minute = requests_per_minute
        self.max_inflight = max_inflight
        self.inflight = 0
        self.requests = defaultdict(deque)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path", "").rstrip("/") != "/mcp":
            await self.app(scope, receive, send)
            return

        async def reject(status, message, headers=None):
            await JSONResponse({"error": message}, status_code=status, headers=headers)(scope, receive, send)

        if not self.keys:
            await reject(503, "MCP authentication is not configured")
            return
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        auth = headers.get(b"authorization", b"").decode("latin-1")
        scheme, _, token = auth.partition(" ")
        digest = hashlib.sha256(token.encode()).hexdigest()
        owner = None
        if scheme.lower() == "bearer" and 32 <= len(token) <= 4096:
            for candidate, expected in self.keys.items():
                if secrets.compare_digest(digest, expected):
                    owner = candidate
        if owner is None:
            await reject(401, "Valid bearer token required", {"WWW-Authenticate": "Bearer"})
            return
        # Browsers must not send cross-origin requests to this API. Native MCP
        # clients do not send Origin. Configure explicit browser origins if needed.
        origin = headers.get(b"origin")
        allowed = {s.strip() for s in os.getenv("MCP_ALLOWED_ORIGINS", "").split(",") if s.strip()}
        if origin and origin.decode("latin-1") not in allowed:
            await reject(403, "Origin not allowed")
            return
        now = time.monotonic()
        recent = self.requests[owner]
        while recent and recent[0] <= now - 60:
            recent.popleft()
        if len(recent) >= self.requests_per_minute or self.inflight >= self.max_inflight:
            await reject(429, "Request limit reached", {"Retry-After": "60"})
            return
        # Bound memory before the MCP transport parses attacker-controlled JSON.
        max_body = 1024 * 1024
        try:
            if int(headers.get(b"content-length", b"0")) > max_body:
                await reject(413, "Request body too large")
                return
        except ValueError:
            await reject(400, "Invalid content length")
            return
        body = bytearray()
        async def read_body():
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return False
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > max_body:
                    return None
                body.extend(chunk)
                if not message.get("more_body", False):
                    return True
        try:
            complete = await asyncio.wait_for(read_body(), timeout=15)
        except TimeoutError:
            await reject(408, "Request body timed out")
            return
        if complete is None:
            await reject(413, "Request body too large")
            return
        if not complete:
            return
        replayed = False
        async def bounded_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()
        if len(recent) >= self.requests_per_minute or self.inflight >= self.max_inflight:
            await reject(429, "Request limit reached", {"Retry-After": "60"})
            return
        recent.append(now)
        self.inflight += 1
        context_token = authenticated_owner.set(owner)
        try:
            await self.app(scope, bounded_receive, send)
        finally:
            authenticated_owner.reset(context_token)
            self.inflight -= 1
