from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable
import base64

import plotly.graph_objects as go
import mcp.types as types

from mcp.server.fastmcp import FastMCP
from mcp.server.streamable_http import StreamableHTTPServerTransport
from mcp.server.transport_security import TransportSecuritySettings

from core.data_loader import fetch_data
from main import get_dynamic_tools, run_generate_optimized_verdict, serialize_output
from tools.intelligence.company_profile import get_company_info
from tools.intelligence.plotly_dashboard import build_chart_pack
from tools.strategies.sector_pipeline import find_sector_stock_pipeline


def _enable_mcpjam_compatibility() -> None:
    """Relax strict Accept checks for browser-based MCP clients.

    Some web clients cannot reliably set a fully custom Accept header and may
    send `*/*` or only one media type. This shim keeps FastMCP functional while
    remaining strict enough for JSON-RPC content-type validation.
    """

    original = StreamableHTTPServerTransport._check_accept_headers

    def _patched_check_accept_headers(self, request):  # type: ignore[override]
        has_json, has_sse = original(self, request)
        accept_header = request.headers.get("accept", "")

        # Browser clients and some MCP UIs may use wildcard Accept values.
        if not accept_header or "*/*" in accept_header:
            return True, True

        # Treat either media type as acceptable for compatibility.
        if has_json and not has_sse:
            has_sse = True
        if has_sse and not has_json:
            has_json = True

        return has_json, has_sse

    StreamableHTTPServerTransport._check_accept_headers = _patched_check_accept_headers


_enable_mcpjam_compatibility()


def _load_server_instructions() -> str:
    policy_prefix = (
        "MANDATORY STYLE POLICY: Use professional quantitative language. "
        "Do not use emojis. Do not use decorative symbols.\n\n"
    )
    instructions_path = Path(__file__).resolve().parent / "mcp-instructions.md"
    try:
        return policy_prefix + instructions_path.read_text(encoding="utf-8").strip()
    except Exception:
        return (
            policy_prefix
            + "Institutional quant MCP server. Use risk-adjusted metrics, "
            "alpha/beta decomposition, regime checks, and VaR-aware verdicts."
        )

mcp = FastMCP(
    "mcp-quant-brain",
    instructions=_load_server_instructions(),
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
    streamable_http_path="/mcp",
    stateless_http=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
def generate_optimized_verdict(
    tickers: list[str],
    amount: float = 10000,
    optimize_type: str = "mvo",
) -> dict:
    """Optimize a portfolio and return backtest metrics plus a final verdict.

    Args:
        tickers: List of ticker symbols (e.g. ["AAPL", "RELIANCE.NS"])
        amount: Investment amount used for allocation context
        optimize_type: Optimization mode. Supported values are:
            "mvo", "hrp", "max_sharpe", "min_volatility",
            "black_litterman", "cvar", "semivariance".
    """
    result = run_generate_optimized_verdict(tickers, amount, optimize_type)
    return serialize_output(result)


@mcp.tool()
def get_company_profile(ticker: str) -> dict:
    """Return a full company snapshot with business, valuation, and market metadata."""
    return serialize_output(get_company_info(ticker))


@mcp.tool()
def find_sector_stock_pipeline_tool(
    market: str = "india",
    top_n_sectors: int = 3,
    top_n_stocks: int = 3,
) -> dict:
    """Run a multi-step pipeline: sector performance -> stock ranking -> strategy selection."""
    return serialize_output(
        find_sector_stock_pipeline(
            market=market,
            top_n_sectors=top_n_sectors,
            top_n_stocks=top_n_stocks,
        )
    )


def _run_optimizer_variant(
    tickers: list[str],
    amount: float,
    optimize_type: str,
) -> dict:
    """Expose each optimizer mode as a first-class MCP tool."""
    result = run_generate_optimized_verdict(tickers, amount, optimize_type)
    return serialize_output(result)


def _run_strategy_module(
    ticker: str,
    module_path: str,
    runner_name: str,
    **kwargs: Any,
) -> dict:
    """Load strategy module lazily and run the requested entrypoint."""
    import importlib

    df, err = fetch_data(ticker)
    if err:
        return {"error": err}

    try:
        module = importlib.import_module(module_path)
        runner: Callable[..., dict] = getattr(module, runner_name)
    except Exception as exc:
        return {
            "error": (
                f"Failed to load strategy module '{module_path}.{runner_name}': {exc}"
            )
        }

    try:
        return serialize_output(runner(df, **kwargs))
    except Exception as exc:
        return {
            "error": (
                f"Strategy execution failed for '{module_path}.{runner_name}': {exc}"
            )
        }


def _image_contents_from_chart_pack(chart_pack: dict[str, Any], limit: int = 8) -> list[types.Content]:
    """Convert chart figures into MCP content blocks that clients can render."""
    contents: list[types.Content] = []
    chart_order = chart_pack.get("default_display", {}).get("pinned", [])
    charts = chart_pack.get("charts", {})

    if not chart_order:
        chart_order = list(charts.keys())[:limit]

    for chart_id in chart_order[:limit]:
        figure_json = charts.get(chart_id)
        if not figure_json:
            continue

        try:
            figure = go.Figure(figure_json)
            image_bytes = figure.to_image(format="png", width=1280, height=720, scale=2)
            image_b64 = base64.b64encode(image_bytes).decode("ascii")
            title = chart_pack.get("chart_specs", {}).get(chart_id, {}).get("title", chart_id)
            contents.append(types.TextContent(type="text", text=f"### {title}"))
            contents.append(
                types.ImageContent(
                    type="image",
                    data=image_b64,
                    mimeType="image/png",
                )
            )
        except Exception as exc:
            contents.append(types.TextContent(type="text", text=f"{chart_id}: chart image unavailable ({exc})"))

    if not contents:
        contents.append(types.TextContent(type="text", text="No chart images could be generated."))

    return contents


@mcp.tool()
def optimize_mvo(tickers: list[str], amount: float = 10000) -> dict:
    """Optimize portfolio using MVO and return full verdict payload."""
    return _run_optimizer_variant(tickers, amount, "mvo")


@mcp.tool()
def optimize_hrp(tickers: list[str], amount: float = 10000) -> dict:
    """Optimize portfolio using HRP and return full verdict payload."""
    return _run_optimizer_variant(tickers, amount, "hrp")


@mcp.tool()
def optimize_max_sharpe(tickers: list[str], amount: float = 10000) -> dict:
    """Optimize portfolio for max Sharpe and return full verdict payload."""
    return _run_optimizer_variant(tickers, amount, "max_sharpe")


@mcp.tool()
def optimize_min_volatility(tickers: list[str], amount: float = 10000) -> dict:
    """Optimize portfolio for minimum volatility and return full verdict payload."""
    return _run_optimizer_variant(tickers, amount, "min_volatility")


@mcp.tool()
def optimize_black_litterman(tickers: list[str], amount: float = 10000) -> dict:
    """Optimize portfolio using Black-Litterman and return full verdict payload."""
    return _run_optimizer_variant(tickers, amount, "black_litterman")


@mcp.tool()
def optimize_cvar(tickers: list[str], amount: float = 10000) -> dict:
    """Optimize portfolio using CVaR and return full verdict payload."""
    return _run_optimizer_variant(tickers, amount, "cvar")


@mcp.tool()
def optimize_semivariance(tickers: list[str], amount: float = 10000) -> dict:
    """Optimize portfolio using semivariance and return full verdict payload."""
    return _run_optimizer_variant(tickers, amount, "semivariance")


@mcp.tool()
def backtest_macd_momentum(ticker: str) -> dict:
    """Run MACD momentum strategy backtest for one ticker."""
    return _run_strategy_module(ticker, "tools.strategies.macd_momentum", "run_strategy")


@mcp.tool()
def backtest_macd_trend_follower(
    ticker: str,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict:
    """Run MACD trend follower strategy backtest for one ticker."""
    return _run_strategy_module(
        ticker,
        "tools.strategies.macd_trend_follower",
        "run_backtest",
        fast=fast,
        slow=slow,
        signal=signal,
    )


@mcp.tool()
def backtest_mean_reversion_rsi_bb(
    ticker: str,
    rsi_lower: int = 30,
    rsi_upper: int = 70,
) -> dict:
    """Run RSI + Bollinger Band mean-reversion strategy backtest."""
    return _run_strategy_module(
        ticker,
        "tools.strategies.mean_reversion_rsi_bb",
        "run_strategy",
        rsi_lower=rsi_lower,
        rsi_upper=rsi_upper,
    )


@mcp.tool()
def backtest_rsi_mean_reversion(
    ticker: str,
    length: int = 14,
    lower: int = 30,
    upper: int = 70,
) -> dict:
    """Run RSI mean-reversion strategy backtest."""
    return _run_strategy_module(
        ticker,
        "tools.strategies.rsi_mean_reversion",
        "run_backtest",
        length=length,
        lower=lower,
        upper=upper,
    )


@mcp.tool()
def backtest_sma_crossover(ticker: str, fast: int = 50, slow: int = 200) -> dict:
    """Run SMA crossover strategy backtest."""
    return _run_strategy_module(
        ticker,
        "tools.strategies.sma_crossover_bt",
        "run_backtest",
        fast=fast,
        slow=slow,
    )


@mcp.tool()
def backtest_trend_crossover(ticker: str, fast: int = 50, slow: int = 200) -> dict:
    """Run trend crossover strategy backtest."""
    return _run_strategy_module(
        ticker,
        "tools.strategies.trend_crossover",
        "run_strategy",
        fast=fast,
        slow=slow,
    )


@mcp.tool()
def backtest_volatility_breakout(ticker: str, length: int = 20) -> dict:
    """Run volatility breakout strategy backtest."""
    return _run_strategy_module(
        ticker,
        "tools.strategies.volatility_breakout",
        "run_backtest",
        length=length,
    )


@mcp.tool()
def backtest_universal_indicator(
    ticker: str,
    indicator_name: str,
) -> dict:
    """Run universal indicator backtest for a given indicator on one ticker."""
    return _run_strategy_module(
        ticker,
        "tools.strategies.universal_bt",
        "run_universal_backtest",
        indicator_name=indicator_name,
    )


@mcp.tool()
def generate_chart_pack(
    tickers: list[str],
    amount: float = 10000,
    market: str = "us",
    company_ticker: str = "",
    timeframe: str = "2y",
) -> dict:
    """Generate the full institutional chart suite for dashboard rendering."""
    target_company = company_ticker.strip() if company_ticker else None
    return serialize_output(
        build_chart_pack(
            tickers=tickers,
            amount=amount,
            market=market,
            company_ticker=target_company,
            timeframe=timeframe,
        )
    )


@mcp.tool()
def generate_charts(
    tickers: list[str],
    amount: float = 10000,
    market: str = "us",
    company_ticker: str = "",
    timeframe: str = "2y",
) -> list[types.Content]:
    """Generate charts for portfolio, strategy, quant, fundamentals, and sector pipeline."""
    target_company = company_ticker.strip() if company_ticker else None
    chart_pack = build_chart_pack(
        tickers=tickers,
        amount=amount,
        market=market,
        company_ticker=target_company,
        timeframe=timeframe,
    )
    summary = serialize_output({
        "status": chart_pack.get("status"),
        "chart_count": chart_pack.get("chart_count"),
        "timeframe": chart_pack.get("meta", {}).get("timeframe"),
        "pinned": chart_pack.get("default_display", {}).get("pinned", []),
    })
    return [types.TextContent(type="text", text=json.dumps(summary, indent=2))] + _image_contents_from_chart_pack(chart_pack)


@mcp.tool()
def plot_charts(
    tickers: list[str],
    amount: float = 10000,
    market: str = "us",
    company_ticker: str = "",
    timeframe: str = "2y",
) -> list[types.Content]:
    """Alias for chart generation; kept for natural plotting language in clients."""
    target_company = company_ticker.strip() if company_ticker else None
    chart_pack = build_chart_pack(
        tickers=tickers,
        amount=amount,
        market=market,
        company_ticker=target_company,
        timeframe=timeframe,
    )
    summary = serialize_output({
        "status": chart_pack.get("status"),
        "chart_count": chart_pack.get("chart_count"),
        "timeframe": chart_pack.get("meta", {}).get("timeframe"),
        "pinned": chart_pack.get("default_display", {}).get("pinned", []),
    })
    return [types.TextContent(type="text", text=json.dumps(summary, indent=2))] + _image_contents_from_chart_pack(chart_pack)


def _register_dynamic_tools() -> None:
    dynamic_tools = get_dynamic_tools()

    for tool_name, info in dynamic_tools.items():
        indicator_func = info["func"]
        tool_description = info.get("description") or f"Run {tool_name} for a ticker"

        def _make_tool(func, name: str, description: str):
            def _tool(ticker: str) -> dict:
                """Dynamically generated indicator tool."""
                df, err = fetch_data(ticker)
                if err:
                    return {"error": err}
                return serialize_output(func(df))

            _tool.__name__ = name
            _tool.__doc__ = description
            return _tool

        mcp.tool()(_make_tool(indicator_func, tool_name, tool_description))


_register_dynamic_tools()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
