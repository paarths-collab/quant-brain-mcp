import asyncio
import json
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

import sys

def log(msg: str):
    """Print to stderr for host to see logs without polluting stdout."""
    print(f"[LOG] {msg}", file=sys.stderr)

# Initialize the low-level MCP server
server = Server("mcp-quant-brain")

# Discover dynamic tools lazily to keep MCP startup fast enough for host timeouts.
_dynamic_tools = None


def serialize_output(obj):
    from utils.serializer import serialize_output as _serialize_output
    return _serialize_output(obj)


def get_dynamic_tools():
    global _dynamic_tools
    if _dynamic_tools is None:
        from core.registry import register_all_tools
        _dynamic_tools = register_all_tools()
    return _dynamic_tools

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available financial and optimization tools."""
    tools = [
        types.Tool(
            name="generate_optimized_verdict",
            description="The Ultimate Tool: Optimizes a cross-market portfolio (US/India), backtests it, and provides a final Verdict.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "List of stock tickers (e.g. ['AAPL', 'RELIANCE.NS'])"
                    },
                    "amount": {
                        "type": "number", 
                        "default": 10000,
                        "description": "Investment amount for allocation"
                    },
                    "optimize_type": {
                        "type": "string",
                        "enum": ["mvo", "hrp"],
                        "default": "mvo",
                        "description": "Strategy for portfolio optimization (Mean-Variance vs Hierarchical Risk Parity)"
                    }
                },
                "required": ["tickers"]
            }
        )
    ]
    
    # Add dynamically discovered tools
    dynamic_tools = get_dynamic_tools()
    for name, info in dynamic_tools.items():
        tools.append(types.Tool(
            name=name,
            description=info["description"],
            inputSchema=info["parameters"]
        ))
        
    return tools

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """Route tool calls to the appropriate logic."""
    try:
        if not arguments:
            arguments = {}

        if name == "generate_optimized_verdict":
            log(f"Calling generate_optimized_verdict with {arguments}")
            tickers = arguments.get("tickers", [])
            amount = arguments.get("amount", 10000)
            optimize_type = arguments.get("optimize_type", "mvo")
            result = run_generate_optimized_verdict(tickers, amount, optimize_type)
            # Serialize the result before dumping to JSON
            safe_result = serialize_output(result)
            return [types.TextContent(type="text", text=json.dumps(safe_result, indent=2))]

        dynamic_tools = get_dynamic_tools()
        if name in dynamic_tools:
            log(f"Calling dynamic tool {name} with {arguments}")
            ticker = arguments.get("ticker")
            if not ticker:
                return [types.TextContent(type="text", text="Error: 'ticker' parameter is required.")]
            
            # Execute the dynamic tool's function
            func = dynamic_tools[name]["func"]
            # Most indicators expect a df. We'll fetch it here.
            from core.data_loader import fetch_data
            df, err = fetch_data(ticker)
            if err:
                return [types.TextContent(type="text", text=f"Error: {err}")]
            
            result = func(df)
            safe_result = serialize_output(result)
            return [types.TextContent(type="text", text=json.dumps(safe_result, indent=2))]

        return [types.TextContent(type="text", text=f"Unknown Tool: {name}")]
        
    except Exception as e:
        log(f"FATAL TOOL ERROR: {str(e)}")
        import traceback
        log(traceback.format_exc())
        return [types.TextContent(type="text", text=f"Tool Error: {str(e)}")]

def run_generate_optimized_verdict(tickers: list, amount: float, optimize_type: str = "mvo"):
    """Internal logic for the optimized verdict tool."""
    import pandas as pd
    from core.data_loader import fetch_data
    from core.forex import normalize_prices
    from tools.intelligence.engine import get_quant_context
    from tools.optimization.mean_variance import run_mvo_basic
    from tools.optimization.hierarchical_risk_parity import optimize as run_hrp_optimize
    from tools.backtesting.portfolio_bt import backtest_optimized_portfolio

    data_dict = {}
    ohlc_frames = {}
    for t in tickers:
        df, err = fetch_data(t)
        if not err and not df.empty:
            df.index = df.index.tz_localize(None).normalize()
            ohlc_frames[t] = df
            data_dict[t] = df[~df.index.duplicated(keep='last')]['Close']
    
    if not data_dict:
        return {"error": "Could not fetch data for provided tickers."}

    price_df = pd.DataFrame(data_dict).ffill().dropna()
    
    try:
        # Step 1: Optimize
        if optimize_type == "hrp":
            opt_results = run_hrp_optimize(price_df)
            weights = opt_results['optimized_weights']
        else:
            normalized_df = normalize_prices(price_df.copy())
            returns = normalized_df.pct_change().dropna()
            mu = returns.mean() * 252
            S = returns.cov() * 252
            opt_results = run_mvo_basic(mu, S)
            weights = opt_results['weights']
        
        # Step 2: Backtest
        bt_results = backtest_optimized_portfolio(price_df, weights)
        actual_sharpe = float(bt_results['portfolio_sharpe'])
        
        # Step 3: Smart context on a representative market series
        intel = None
        intel_ticker = None
        for ticker in tickers:
            if ticker in ohlc_frames:
                intel_ticker = ticker
                break

        if intel_ticker:
            try:
                intel = get_quant_context(ohlc_frames[intel_ticker])
            except Exception as intel_err:
                intel = {"warning": f"Intelligence engine failed: {intel_err}"}

        # Step 4: Verdicts
        backtest_verdict = "STAY AWAY"
        if actual_sharpe > 1.2:
            backtest_verdict = "STRONG BUY"
        elif actual_sharpe > 0.7:
            backtest_verdict = "PROPER"

        institutional_verdict = backtest_verdict
        if isinstance(intel, dict) and intel.get("institutional_verdict"):
            institutional_verdict = str(intel["institutional_verdict"])

        reasoning = (
            f"Portfolio optimization ({optimize_type.upper()}) produced Sharpe {actual_sharpe:.2f}, "
            f"total return {bt_results['portfolio_total_return']}, and max drawdown {bt_results['portfolio_drawdown']}."
        )

        if isinstance(intel, dict) and intel.get("regime") and intel.get("consensus_score"):
            reasoning += (
                f" Market context on {intel_ticker}: {intel['regime']}; "
                f"consensus={intel['consensus_score']}."
            )

        res = {
            "recommended_weights": weights,
            "intelligence": intel,
            "intelligence_ticker": intel_ticker,
            "backtest_metrics": bt_results,
            "backtest_verdict": backtest_verdict,
            "final_verdict": institutional_verdict,
            "reasoning": reasoning,
            "optimization_method": optimize_type.upper()
        }
        return serialize_output(res)
    except Exception as e:
        return serialize_output({"error": f"Optimization logic failed: {str(e)}"})

async def main():
    """Main entry point for the stdio server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-quant-brain",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
