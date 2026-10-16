"""Adapter boundary tests; no model calls or credentials required."""
import asyncio
from types import SimpleNamespace

import pytest

from core.research_runtime import CodexResearchRuntime, ResearchRuntimeError, _strict_schema


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeSDK:
    def __init__(self, config):
        self.config = config
        self.closed = False
        self.thread_options = None
        self.run_options = None
        self.block = False
        self.signed_in = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        self.closed = True

    async def account(self):
        return SimpleNamespace(account=object() if self.signed_in else None)

    async def thread_start(self, **kwargs):
        self.thread_options = kwargs
        return self

    async def run(self, prompt, **kwargs):
        self.run_options = kwargs
        if self.block:
            await asyncio.sleep(100)
        return SimpleNamespace(status="completed", final_response='{"summary":"Test"}')


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    pytest.importorskip("openai_codex")
    monkeypatch.setenv("QUANT_CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setenv("QUANT_INTERNAL_TOKEN", "test-only-placeholder")
    instances = []
    def factory(config):
        client = FakeSDK(config)
        instances.append(client)
        return client
    return CodexResearchRuntime(sdk_factory=factory), instances


@pytest.mark.anyio
async def test_official_sdk_configuration_and_cleanup(runtime):
    runner, instances = runtime
    result = await runner.run("company", "research request")
    client = instances[0]
    assert result["summary"] == "Test"
    assert client.closed
    assert client.thread_options["ephemeral"] is True
    assert client.thread_options["sandbox"].value == "read-only"
    overrides = "\n".join(client.config.config_overrides)
    assert 'web_search="live"' in overrides
    assert "features.shell_tool=false" in overrides
    assert "features.apps=false" in overrides
    assert 'approval_policy="never"' in overrides
    assert "test-only-placeholder" not in overrides
    assert "start_research" not in overrides
    assert client.config.env["CODEX_HOME"] == str(runner.home)


@pytest.mark.anyio
async def test_readiness_does_not_claim_live_success(runtime):
    runner, instances = runtime
    status = await runner.readiness()
    assert status["authenticated"]
    assert status["live_research_tested"] is False
    assert instances[0].thread_options is None
    assert instances[0].closed


@pytest.mark.anyio
async def test_cancellation_closes_subprocess(runtime):
    runner, instances = runtime
    original = runner.sdk_factory
    def blocking(config):
        client = original(config)
        client.block = True
        return client
    runner.sdk_factory = blocking
    task = asyncio.create_task(runner.run("company", "request"))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert instances[0].closed


@pytest.mark.anyio
async def test_signed_out_failure_is_safe(runtime):
    runner, instances = runtime
    original = runner.sdk_factory
    def signed_out(config):
        client = original(config)
        client.signed_in = False
        return client
    runner.sdk_factory = signed_out
    with pytest.raises(ResearchRuntimeError, match="not signed in"):
        await runner.run("company", "request")
    assert instances[0].closed


def test_no_remote_plaintext_credentials(monkeypatch):
    monkeypatch.setenv("QUANT_INTERNAL_MCP_URL", "http://remote.example/mcp")
    with pytest.raises(ValueError, match="HTTPS"):
        CodexResearchRuntime()


def test_strict_schema_recurses_without_mutating_input():
    schema = {"type": "object", "properties": {"x": {"type": "string", "default": "a"}}, "$defs": {"nested": {"type": "object", "properties": {"y": {"type": "number"}}}}}
    converted = _strict_schema(schema)
    assert converted["required"] == ["x"]
    assert converted["$defs"]["nested"]["additionalProperties"] is False
    assert "default" not in converted["properties"]["x"]
    assert schema["properties"]["x"]["default"] == "a"


@pytest.mark.anyio
async def test_timeout_closes_process(runtime):
    runner, instances = runtime
    runner.timeout_seconds = 0.01
    original = runner.sdk_factory
    def blocking(config):
        client = original(config)
        client.block = True
        return client
    runner.sdk_factory = blocking
    with pytest.raises(ResearchRuntimeError, match="time budget"):
        await runner.run("quant", "request")
    assert instances[0].closed


@pytest.mark.anyio
async def test_disables_inherited_connectors_and_plugins(runtime):
    runner, instances = runtime
    runner.home.mkdir()
    (runner.home / "config.toml").write_text('[mcp_servers.unrelated]\ncommand="do-not-run"\n[plugins."private@example"]\nenabled=true\n')
    await runner.readiness()
    overrides = instances[0].config.config_overrides
    assert 'mcp_servers={}' in overrides
    assert 'plugins={}' in overrides


@pytest.mark.anyio
async def test_provider_error_does_not_leak_secrets(runtime):
    runner, instances = runtime
    original = runner.sdk_factory
    def failing(config):
        client = original(config)
        async def fail(**kwargs):
            raise RuntimeError("secret-provider-payload")
        client.thread_start = fail
        return client
    runner.sdk_factory = failing
    with pytest.raises(ResearchRuntimeError) as captured:
        await runner.run("company", "request")
    assert "secret-provider-payload" not in str(captured.value)
    assert instances[0].closed


@pytest.mark.anyio
async def test_constructor_error_does_not_leak_provider_payload(runtime):
    runner, _ = runtime
    def failing_factory(config):
        raise RuntimeError("private-constructor-payload")
    runner.sdk_factory = failing_factory
    with pytest.raises(ResearchRuntimeError) as captured:
        await runner.readiness()
    assert "private-constructor-payload" not in str(captured.value)


@pytest.mark.anyio
async def test_cleanup_error_does_not_leak_provider_payload(runtime):
    runner, _ = runtime
    original = runner.sdk_factory
    def failing_cleanup(config):
        client = original(config)
        async def close():
            raise RuntimeError("private-cleanup-payload")
        client.close = close
        return client
    runner.sdk_factory = failing_cleanup
    with pytest.raises(ResearchRuntimeError, match="cleanup failed") as captured:
        await runner.readiness()
    assert "private-cleanup-payload" not in str(captured.value)


def test_execution_events_only_capture_safe_observed_metadata():
    from core.research_runtime import _execution_events
    observed = SimpleNamespace(items=[
        SimpleNamespace(root=SimpleNamespace(type="mcpToolCall", server="quant_internal", tool="get_quote", status="failed", error="private error", arguments="private args", result="private result")),
        SimpleNamespace(root=SimpleNamespace(type="webSearch", query="private query", results=["private data"])),
        SimpleNamespace(root=SimpleNamespace(type="mcpToolCall", server="unrelated", tool="private tool", status="completed")),
        SimpleNamespace(root=SimpleNamespace(type="agentMessage", text="private reasoning")),
    ])
    assert _execution_events(observed) == [
        {"type": "mcpToolCall", "server": "quant_internal", "tool": "get_quote", "status": "failed", "has_error": True},
        {"type": "webSearch"},
    ]


@pytest.mark.anyio
async def test_runtime_executions_are_separate_from_model_json(runtime):
    runner, _ = runtime
    response = await runner.run("company", "request")
    assert response == {"summary": "Test"}
    assert runner.executions == [{"role": "company", "tool_events": []}]
