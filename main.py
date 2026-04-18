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
                        "enum": ["mvo", "hrp", "max_sharpe", "min_volatility", "black_litterman", "cvar", "semivariance"],
                        "default": "mvo",
                        "description": "Portfolio optimization strategy. Supported: mvo, hrp, max_sharpe, min_volatility, black_litterman, cvar, semivariance."
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
    from tools.intelligence.alpha_engine import calculate_alpha_metrics
    from tools.intelligence.engine import get_quant_analysis
    from tools.optimization.mean_variance import run_mvo_basic
    from tools.optimization.hierarchical_risk_parity import optimize as run_hrp_optimize
    from tools.backtesting.portfolio_bt import backtest_optimized_portfolio

    def _infer_benchmark_ticker(symbol: str) -> str:
        sym = str(symbol).upper()
        if sym.endswith((".NS", ".BO")):
            return "^NSEI"
        return "^GSPC"

    def _to_float_pct(value, default: float = 0.0) -> float:
        try:
            return float(str(value).replace("%", "").strip())
        except Exception:
            return default

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
        opt_key = str(optimize_type or "mvo").strip().lower()
        normalized_df = normalize_prices(price_df.copy())
        returns = normalized_df.pct_change(fill_method=None).dropna()
        mu = returns.mean() * 252
        S = returns.cov() * 252

        if opt_key == "hrp":
            opt_results = run_hrp_optimize(price_df)
            weights = opt_results["optimized_weights"]
        elif opt_key == "min_volatility":
            opt_results = run_mvo_basic(mu, S, target="min_volatility")
            weights = opt_results["weights"]
        elif opt_key == "max_sharpe":
            from tools.optimization.markowitz_mvo import optimize as run_markowitz_optimize

            opt_results = run_markowitz_optimize(normalized_df)
            weights = opt_results["optimized_weights"]
        elif opt_key == "black_litterman":
            from pypfopt import EfficientFrontier
            from tools.optimization.black_litterman import optimize as run_black_litterman_optimize

            implied_views = None
            if not mu.empty:
                best_asset = str(mu.idxmax())
                implied_views = {best_asset: float(mu.loc[best_asset])}

            bl_res = run_black_litterman_optimize(normalized_df, views=implied_views)
            posterior_returns = pd.Series(bl_res["posterior_returns"])
            posterior_cov = pd.DataFrame(bl_res["posterior_covariance"])
            ef = EfficientFrontier(posterior_returns, posterior_cov)
            ef.max_sharpe()
            weights = ef.clean_weights()
            opt_results = {"optimized_weights": weights, **bl_res}
        elif opt_key in {"cvar", "semivariance"}:
            from tools.optimization.efficient_frontier import run_advanced_frontier

            adv = run_advanced_frontier(returns, method=opt_key)
            weights = adv["weights"]
            opt_results = adv
        else:
            # Default to MVO (max Sharpe on mean/cov estimates)
            opt_key = "mvo"
            opt_results = run_mvo_basic(mu, S, target="max_sharpe")
            weights = opt_results["weights"]
        
        # Step 2: Backtest
        bt_results = backtest_optimized_portfolio(price_df, weights)
        actual_sharpe = float(bt_results['portfolio_sharpe'])
        
        # Step 3: Institutional intelligence on a representative market series
        quant_analysis = None
        alpha_analysis = None
        intel_ticker = None
        benchmark_ticker = None
        for ticker in tickers:
            if ticker in ohlc_frames:
                intel_ticker = ticker
                break

        if intel_ticker:
            benchmark_ticker = _infer_benchmark_ticker(intel_ticker)
            try:
                quant_analysis = get_quant_analysis(
                    ohlc_frames[intel_ticker],
                    benchmark_ticker=benchmark_ticker,
                )
            except Exception as quant_err:
                quant_analysis = {"error": f"Quant engine failed: {quant_err}"}

            try:
                alpha_analysis = calculate_alpha_metrics(
                    ohlc_frames[intel_ticker],
                    benchmark_ticker=benchmark_ticker,
                )
            except Exception as alpha_err:
                alpha_analysis = {"error": f"Alpha engine failed: {alpha_err}"}

        # Step 4: Risk-adjusted verdicts
        backtest_verdict = "STAY AWAY"
        if actual_sharpe > 1.2:
            backtest_verdict = "STRONG BUY"
        elif actual_sharpe > 0.7:
            backtest_verdict = "PROPER"

        alpha_value = None
        beta_value = None
        r_squared = None
        if isinstance(alpha_analysis, dict) and "error" not in alpha_analysis:
            alpha_value = alpha_analysis.get("alpha_annualized")
            beta_value = alpha_analysis.get("beta")
            r_squared = alpha_analysis.get("r_squared")

        strategic_verdict = backtest_verdict
        if isinstance(alpha_value, (int, float)):
            if alpha_value < 0:
                strategic_verdict = "REDUCE"
            elif actual_sharpe >= 0.9 and alpha_value > 0.02:
                strategic_verdict = "ACCUMULATE"
            else:
                strategic_verdict = "NEUTRAL"

        one_day_var_pct = 0.0
        if isinstance(quant_analysis, dict) and "error" not in quant_analysis:
            one_day_var_pct = _to_float_pct(quant_analysis.get("one_day_var_95"), 0.0)

        capital_at_risk = abs(one_day_var_pct) / 100 * float(amount)
        capital_plan = "LUMP_SUM_ACCEPTABLE"
        if float(amount) <= 5000 and capital_at_risk > (0.025 * float(amount)):
            capital_plan = "SIP_PREFERRED"

        factor_exposure = "SYSTEMATIC_BETA"
        if isinstance(alpha_value, (int, float)) and alpha_value > 0.05:
            factor_exposure = "IDIOSYNCRATIC_ALPHA"

        risk_flags = []
        if isinstance(beta_value, (int, float)) and beta_value > 1.5:
            risk_flags.append("High systematic sensitivity (beta > 1.5)")
        if isinstance(r_squared, (int, float)) and r_squared > 0.9:
            risk_flags.append("Closet indexer risk (R-squared > 0.9)")
        if one_day_var_pct < -3.0:
            risk_flags.append("Tail risk elevated (95% 1-day VaR below -3%)")

        reasoning = (
            f"Portfolio optimization ({opt_key.upper()}) produced Sharpe {actual_sharpe:.2f}, "
            f"total return {bt_results['portfolio_total_return']}, and max drawdown {bt_results['portfolio_drawdown']}."
        )

        if isinstance(quant_analysis, dict) and "error" not in quant_analysis:
            reasoning += (
                f" Regime check on {intel_ticker} versus {benchmark_ticker}: {quant_analysis.get('regime')}; "
                f"Hurst={quant_analysis.get('hurst_exponent')}, Beta={quant_analysis.get('beta')}, "
                f"VaR95={quant_analysis.get('one_day_var_95')}."
            )

        if isinstance(alpha_analysis, dict) and "error" not in alpha_analysis:
            reasoning += (
                f" Alpha/Beta regression: alpha={alpha_analysis.get('alpha_annualized_pct')}, "
                f"beta={alpha_analysis.get('beta')}, R-squared={alpha_analysis.get('r_squared')}."
            )

        reasoning += (
            f" Estimated 95% one-day capital-at-risk on notional {amount} is {capital_at_risk:.2f}. "
            f"Capital plan: {capital_plan}."
        )

        if risk_flags:
            reasoning += " Risk flags: " + "; ".join(risk_flags) + "."

        if isinstance(quant_analysis, dict) and quant_analysis.get("regime") == "MEAN_REVERTING":
            reasoning += " Regime filter: avoid pure trend-following entries while mean reversion dominates."

        res = {
            "recommended_weights": weights,
            "intelligence": quant_analysis,
            "quant_analysis": quant_analysis,
            "alpha_analysis": alpha_analysis,
            "factor_exposure": factor_exposure,
            "risk_assessment": {
                "one_day_var_95_pct": f"{one_day_var_pct:.2f}%",
                "one_day_var_95_amount": round(capital_at_risk, 2),
                "capital_plan": capital_plan,
                "risk_flags": risk_flags,
            },
            "intelligence_ticker": intel_ticker,
            "benchmark_ticker": benchmark_ticker,
            "backtest_metrics": bt_results,
            "backtest_verdict": backtest_verdict,
            "final_verdict": strategic_verdict,
            "strategic_verdict": strategic_verdict,
            "reasoning": reasoning,
            "optimization_method": opt_key.upper(),
            "supported_optimization_types": [
                "mvo",
                "hrp",
                "max_sharpe",
                "min_volatility",
                "black_litterman",
                "cvar",
                "semivariance",
            ],
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
