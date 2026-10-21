"""Isolated, bounded adapter for the official Codex Python SDK.

Authentication is owned by Codex. This module never reads, copies or logs tokens.
Defaults to a dedicated CODEX_HOME; explicit configuration can reuse an existing sign-in.
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from core.research_workflow import schema_for_role
from core.risk_state import count_unavailable


class ResearchRuntimeError(RuntimeError):
    """A safe-to-display runtime failure without provider output or credentials."""


ResearchConfigurationError = ResearchRuntimeError


def _strict_schema(schema: dict) -> dict:
    """Convert Pydantic defaults to the provider's strict structured-output schema."""
    schema = json.loads(json.dumps(schema))

    def visit(node):
        if isinstance(node, dict):
            node.pop("default", None)
            node.pop("format", None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(schema)
    return schema


def _execution_events(result) -> list[dict]:
    """Record SDK-observed tool use without prompts, arguments, results or URLs."""
    from core.research_tools import ALLOWED_TOOLS

    events = []
    for wrapped in getattr(result, "items", ()):
        item = getattr(wrapped, "root", wrapped)
        kind = getattr(item, "type", None)
        if kind == "mcpToolCall":
            if getattr(item, "server", None) != "quant_internal" or getattr(item, "tool", None) not in ALLOWED_TOOLS:
                continue
            status = getattr(item, "status", None)
            status = getattr(status, "value", status)
            tool_result = getattr(item, "result", None)
            payload = getattr(tool_result, "structured_content", None)
            has_payload_error = _payload_has_error(payload)
            unavailable_count = count_unavailable(payload)
            for block in getattr(tool_result, "content", ()):
                text = block.get("text") if isinstance(block, dict) else getattr(block, "text", None)
                if isinstance(text, str):
                    try:
                        parsed = json.loads(text)
                    except (ValueError, TypeError):
                        continue
                    has_payload_error |= _payload_has_error(parsed)
                    # The same payload may arrive as structured content and as
                    # text; count it once.
                    unavailable_count = max(unavailable_count, count_unavailable(parsed))
            events.append({"type": "mcpToolCall", "server": "quant_internal", "tool": item.tool,
                           "status": status if status in {"completed", "failed", "inProgress"} else "unknown",
                           "has_error": getattr(item, "error", None) is not None or has_payload_error or unavailable_count > 0,
                           # Present only when non-zero so existing traces keep their shape.
                           **({"risk_unavailable": unavailable_count} if unavailable_count else {})})
        elif kind == "webSearch":
            events.append({"type": "webSearch"})
    return events


def _payload_has_error(payload) -> bool:
    """Detect tool-level failures even when the HTTP/SDK call completed.

    Store only a boolean; provider messages and private tool values stay out of
    the execution trace. Partial grouped-indicator failures count as partial work.
    A metric reported as unavailable is a failure to compute, not a result.
    """
    if isinstance(payload, dict):
        if payload.get("error") or payload.get("isError") is True or payload.get("status") == "unavailable":
            return True
        return any(_payload_has_error(value) for value in payload.values())
    if isinstance(payload, list):
        return any(_payload_has_error(value) for value in payload)
    return False


class CodexResearchRuntime:
    def __init__(self, *, sdk_factory=None, timeout_seconds: float | None = None):
        self.home = Path(os.environ.get("QUANT_CODEX_HOME", "~/.quant-brain/codex")).expanduser().resolve()
        self.url = os.environ.get("QUANT_INTERNAL_MCP_URL", "http://127.0.0.1:8001/mcp")
        parsed = urlsplit(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("QUANT_INTERNAL_MCP_URL must be an HTTP(S) URL without credentials, query or fragment")
        if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Remote internal MCP connections require HTTPS")
        self.model = os.environ.get("QUANT_CODEX_MODEL") or None
        self.timeout_seconds = float(timeout_seconds if timeout_seconds is not None else os.environ.get("QUANT_CODEX_ROLE_TIMEOUT", "120"))
        if not 1 <= self.timeout_seconds <= 600:
            raise ValueError("QUANT_CODEX_ROLE_TIMEOUT must be between 1 and 600 seconds")
        self.sdk_factory = sdk_factory
        self.executions: list[dict] = []

    def _configuration(self, cwd: str):
        from openai_codex import CodexConfig
        from core.research_tools import ALLOWED_TOOLS

        # Do not reuse the desktop's home implicitly. Explicit custom homes may
        # contain configuration; disable all their connectors and plugins first.
        overrides = [
            'web_search="live"', 'sandbox_mode="read-only"', 'approval_policy="never"',
            'forced_login_method="chatgpt"', 'cli_auth_credentials_store="file"', 'project_doc_max_bytes=0',
            'features.shell_tool=false', 'features.unified_exec=false', 'notify=[]',
            'features.apps=false', 'features.plugins=false', 'features.remote_plugin=false',
            'features.browser_use=false',
            'features.computer_use=false', 'features.multi_agent=false',
            'features.skill_search=false', 'features.skip_host_skill_discovery=true',
            'features.skill_mcp_dependency_install=false',
        ]
        # Replace inherited connector tables before configuring the private MCP.
        # Disabled legacy entries can still fail the CLI's transport validation.
        overrides.extend(['mcp_servers={}', 'plugins={}'])
        overrides.extend([
            'mcp_servers.quant_internal.enabled=true',
            f'mcp_servers.quant_internal.url={json.dumps(self.url)}',
            'mcp_servers.quant_internal.bearer_token_env_var="QUANT_INTERNAL_TOKEN"',
            'mcp_servers.quant_internal.required=true',
            'mcp_servers.quant_internal.tool_timeout_sec=60',
            'mcp_servers.quant_internal.enabled_tools=' + json.dumps(sorted(ALLOWED_TOOLS)),
        ])
        return CodexConfig(cwd=cwd, env={"CODEX_HOME": str(self.home)}, config_overrides=tuple(overrides))

    async def _execute(self, role: str | None, prompt: str = "") -> dict:
        try:
            from openai_codex import AsyncCodex, ApprovalMode, Sandbox
        except ImportError:
            raise ResearchRuntimeError("Install requirements_research.txt to enable Codex research") from None
        if not os.environ.get("QUANT_INTERNAL_TOKEN"):
            raise ResearchRuntimeError("Set QUANT_INTERNAL_TOKEN before enabling research")
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(prefix="quant-research-") as cwd:
            client = None
            try:
                client = (self.sdk_factory or AsyncCodex)(self._configuration(cwd))
                async with asyncio.timeout(self.timeout_seconds):
                    async with client:
                        account = await client.account()
                        if getattr(account, "account", None) is None:
                            raise ResearchRuntimeError("Codex is not signed in: sign in using the selected QUANT_CODEX_HOME, then retry")
                        if role is None:
                            return {"authenticated": True, "runtime": "codex", "live_research_tested": False}
                        thread = await client.thread_start(
                            cwd=cwd, ephemeral=True, model=self.model,
                            approval_mode=ApprovalMode.deny_all, sandbox=Sandbox.read_only,
                            base_instructions="You are a research specialist. Use only web search and the quant_internal MCP tools. Never access local files, credentials, shell commands, external connectors, or trading execution. Follow the supplied research role and evidence policy.",
                        )
                        result = await thread.run(prompt, output_schema=_strict_schema(schema_for_role(role)))
                        self.executions.append({"role": role, "tool_events": _execution_events(result)})
                        status = getattr(result.status, "value", result.status)
                        if status != "completed" or not result.final_response:
                            raise ResearchRuntimeError("Codex research did not complete successfully")
                        parsed = json.loads(result.final_response)
                        if not isinstance(parsed, dict):
                            raise ResearchRuntimeError("Codex returned an invalid research object")
                        return parsed
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                raise ResearchRuntimeError("Codex research exceeded its per-role time budget") from None
            except ResearchRuntimeError:
                raise
            except Exception:
                # Provider exceptions may contain request content or auth data.
                raise ResearchRuntimeError("Codex research failed; check local authentication, MCP availability and model access") from None
            finally:
                # Includes partial context-entry failures and cancelled turns.
                if client is not None:
                    try:
                        await asyncio.shield(client.close())
                    except Exception:
                        raise ResearchRuntimeError("Codex runtime cleanup failed; restart the research worker before retrying") from None

    async def run(self, role: str, prompt: str) -> dict:
        schema_for_role(role)  # Reject unknown roles before starting a process.
        return await self._execute(role, prompt)

    async def readiness(self) -> dict:
        """Check login only; this does not claim model/tool/live-search readiness."""
        return await self._execute(None)
