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
    # optimization (7 optimize_* variants removed: each was byte-for-byte
    # identical to generate_optimized_verdict(optimize_type=...), which
    # already documents and accepts all 7 methods via one parameter)
    "generate_optimized_verdict",
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
    # trader tools
    "get_quote",
    "get_news",
    "build_trade_plan",
    "scan_watchlist",
    "price_alert",
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
    assert len(names) == 25


def test_no_individual_indicator_tools_exposed(server):
    """get_* names are reserved for non-indicator tools; the 38 indicators
    must only surface through the 6 grouped analyze_* tools."""
    allowed_get_tools = {"get_company_profile", "get_quote", "get_news"}
    names = {tool.name for tool in _list_tools(server)}
    assert not any(name.startswith("get_") and name not in allowed_get_tools for name in names)


def test_analyze_momentum_schema(server):
    tool = next(t for t in _list_tools(server) if t.name == "analyze_momentum")
    props = tool.inputSchema["properties"]
    assert "ticker" in props
    assert "indicators" in props
    assert "period" in props
    assert tool.inputSchema["required"] == ["ticker"]


def test_period_parameter_exposed_on_indicator_and_backtest_tools(server):
    tools_by_name = {t.name: t for t in _list_tools(server)}
    for name in (
        "analyze_momentum",
        "analyze_technical_levels",
        "analyze_trend",
        "analyze_volatility",
        "analyze_volume",
        "analyze_statistics",
        "backtest_macd_momentum",
        "backtest_sma_crossover",
        "generate_optimized_verdict",
    ):
        assert "period" in tools_by_name[name].inputSchema["properties"], name


def test_generate_optimized_verdict_documents_all_seven_methods(server):
    """The 7 optimize_* tools were removed because generate_optimized_verdict
    already covers every method via optimize_type -- verify that's still true."""
    tool = next(t for t in _list_tools(server) if t.name == "generate_optimized_verdict")
    enum = tool.inputSchema["properties"]["optimize_type"]["enum"]
    assert set(enum) == {
        "mvo", "hrp", "max_sharpe", "min_volatility",
        "black_litterman", "cvar", "semivariance",
    }


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
