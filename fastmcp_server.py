from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.streamable_http import StreamableHTTPServerTransport
from mcp.server.transport_security import TransportSecuritySettings

from core.data_loader import fetch_data
from main import get_dynamic_tools, run_generate_optimized_verdict, serialize_output


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

mcp = FastMCP(
    "mcp-quant-brain",
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
        optimize_type: Optimization mode, either "mvo" or "hrp"
    """
    result = run_generate_optimized_verdict(tickers, amount, optimize_type)
    return serialize_output(result)


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
    mcp.run()
