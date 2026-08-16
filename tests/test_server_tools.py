"""Tests for the FastMCP server tool surface and metrics endpoint."""

import asyncio
import importlib

import pytest

EXPECTED_TOOLS = {
    # grouped indicators
    "analyze_momentum",
    "analyze_technical_levels",
    "analyze_trend",
    "analyze_volatility",
    "analyze_volume",
    "analyze_statistics",
    # optimization
    "generate_optimized_verdict",
    "optimize_mvo",
    "optimize_hrp",
    "optimize_max_sharpe",
    "optimize_min_volatility",
    "optimize_black_litterman",
    "optimize_cvar",
    "optimize_semivariance",
    # backtests
    "backtest_macd_momentum",
    "backtest_macd_trend_follower",
    "backtest_mean_reversion_rsi_bb",
    "backtest_rsi_mean_reversion",
    "backtest_sma_crossover",
    "backtest_trend_crossover",
    "backtest_volatility_breakout",
    # charts
    "generate_chart_pack",
    "generate_charts",
    "plot_charts",
    # intelligence
    "get_company_profile",
    "find_sector_stock_pipeline_tool",
    "analyze_sector_intelligence_tool",
}


@pytest.fixture(scope="module")
def server():
    return importlib.import_module("fastmcp_server")


def _list_tools(server):
    return asyncio.run(server.mcp.list_tools())


def test_tool_surface_is_exactly_the_curated_set(server):
    names = {tool.name for tool in _list_tools(server)}
    assert names == EXPECTED_TOOLS
    assert len(names) == 27


def test_no_individual_indicator_tools_exposed(server):
    names = {tool.name for tool in _list_tools(server)}
    assert not any(name.startswith("get_") and name != "get_company_profile" for name in names)


def test_analyze_momentum_schema(server):
    tool = next(t for t in _list_tools(server) if t.name == "analyze_momentum")
    props = tool.inputSchema["properties"]
    assert "ticker" in props
    assert "indicators" in props
    assert tool.inputSchema["required"] == ["ticker"]
    assert "rsi" in (tool.description or "")


async def _get(server, path, headers=None):
    """Drive the Starlette app in-process with a minimal ASGI GET request."""
    app = server.mcp.streamable_http_app()
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
    }
    received = {}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            received["status"] = message["status"]
        elif message["type"] == "http.response.body":
            received.setdefault("body", b"")
            received["body"] += message.get("body", b"")

    # Custom routes don't need the MCP session-manager lifespan (which can
    # only start once per process), so call the ASGI app directly.
    await app(scope, receive, send)
    return received


def test_metrics_summary_503_when_token_unset(server, monkeypatch):
    monkeypatch.delenv("METRICS_TOKEN", raising=False)
    response = asyncio.run(_get(server, "/metrics/summary"))
    assert response["status"] == 503


def test_metrics_summary_401_on_bad_token(server, monkeypatch):
    monkeypatch.setenv("METRICS_TOKEN", "secret-token")
    response = asyncio.run(_get(server, "/metrics/summary", {"authorization": "Bearer wrong"}))
    assert response["status"] == 401
    response = asyncio.run(_get(server, "/metrics/summary"))
    assert response["status"] == 401


def test_metrics_summary_503_when_no_database(server, monkeypatch):
    monkeypatch.setenv("METRICS_TOKEN", "secret-token")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    response = asyncio.run(
        _get(server, "/metrics/summary", {"authorization": "Bearer secret-token"})
    )
    assert response["status"] == 503
