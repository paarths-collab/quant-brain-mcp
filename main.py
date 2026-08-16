import asyncio
import json
import math

from core import quant_settings  # noqa: F401  (252-day annualization, applied on import)

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

def _infer_benchmark_ticker(symbol: str) -> str:
    """Pick the appropriate index for a single ticker's alpha/beta regression."""
    sym = str(symbol).upper()
    if sym.endswith((".NS", ".BO")):
        return "^NSEI"
    return "^GSPC"


def _to_float_pct(value, default: float = 0.0) -> float:
    """Parse a value like '-2.50%' into -2.50. Returns `default` on failure."""
    try:
        return float(str(value).replace("%", "").strip())
    except Exception:
        return default


def _compute_portfolio_intelligence(weights: dict, ohlc_frames: dict, infer_benchmark):
    """Run quant/alpha analysis per HELD ticker and blend by portfolio weight.

    Previously only ONE ticker (whichever resolved first) drove every risk
    field -- VaR, beta, alpha, factor_exposure, risk_flags -- regardless of
    portfolio weights. Two users with the identical portfolio in a different
    list order could get different, sometimes contradictory, verdicts.

    Returns (per_ticker: list[dict], blended: dict | None). Tickers whose
    analysis fails (insufficient history, benchmark fetch error, etc.) are
    still reported in per_ticker with their error, but excluded from the
    blend; blend weights are renormalized over the tickers that succeeded.
    blended is None only when every held ticker's analysis failed.
    """
    from core.data_loader import fetch_data
    from tools.intelligence.alpha_engine import calculate_alpha_metrics
    from tools.intelligence.engine import get_quant_analysis

    per_ticker = []
    for ticker, raw_weight in weights.items():
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            continue
        if weight <= 0 or ticker not in ohlc_frames:
            continue

        benchmark = infer_benchmark(ticker)
        entry = {"ticker": ticker, "weight": round(weight, 4), "benchmark": benchmark}

        try:
            entry["quant_analysis"] = get_quant_analysis(ohlc_frames[ticker], benchmark_ticker=benchmark)
        except Exception as exc:
            entry["quant_analysis"] = {"error": str(exc)}

        try:
            entry["alpha_analysis"] = calculate_alpha_metrics(ohlc_frames[ticker], benchmark_ticker=benchmark)
        except Exception as exc:
            entry["alpha_analysis"] = {"error": str(exc)}

        per_ticker.append(entry)

    usable = [
        e
        for e in per_ticker
        if "error" not in e["quant_analysis"] and "error" not in e["alpha_analysis"]
    ]
    total_weight = sum(e["weight"] for e in usable)
    if not usable or total_weight <= 0:
        return per_ticker, None

    def _weighted_avg(values):
        return sum(e["weight"] * v for e, v in zip(usable, values)) / total_weight

    var_pcts = [_to_float_pct(e["quant_analysis"].get("one_day_var_95")) for e in usable]
    betas = [float(e["alpha_analysis"].get("beta", 0.0)) for e in usable]
    alphas = [float(e["alpha_analysis"].get("alpha_annualized", 0.0)) for e in usable]
    r_squareds = [float(e["alpha_analysis"].get("r_squared", 0.0)) for e in usable]

    from collections import Counter

    regimes = [e["quant_analysis"].get("regime") for e in usable if e["quant_analysis"].get("regime")]
    dominant_regime = Counter(regimes).most_common(1)[0][0] if regimes else None

    blended = {
        "one_day_var_95_pct": round(_weighted_avg(var_pcts), 2),
        "beta": round(_weighted_avg(betas), 3),
        "alpha_annualized": round(_weighted_avg(alphas), 4),
        "r_squared": round(_weighted_avg(r_squareds), 3),
        "dominant_regime": dominant_regime,
        "coverage_weight": round(total_weight, 4),
        "tickers_used": [e["ticker"] for e in usable],
    }
    return per_ticker, blended


def run_generate_optimized_verdict(tickers: list, amount: float, optimize_type: str = "mvo"):
    """Internal logic for the optimized verdict tool."""
    import pandas as pd
    from core.data_loader import resolve_ticker
    from tools.optimization.mean_variance import run_mvo_basic
    from tools.optimization.hierarchical_risk_parity import optimize as run_hrp_optimize
    from tools.backtesting.portfolio_bt import backtest_optimized_portfolio

    requested_tickers = list(tickers)
    data_dict = {}
    ohlc_frames = {}
    excluded_tickers = []
    for t in tickers:
        # resolve_ticker (not fetch_data) so the dict key is the symbol that
        # ACTUALLY resolved -- e.g. "RELIANCE" -> "RELIANCE.NS" -- rather than
        # the raw input. Using the raw string here silently mis-benchmarked
        # unsuffixed Indian tickers against the S&P 500 (no ".NS" to detect)
        # and let case variants ("aapl" vs "AAPL") become two "different"
        # portfolio assets instead of one.
        df, err, resolved = resolve_ticker(t)
        if not err and df is not None and not df.empty:
            df.index = df.index.tz_localize(None).normalize()
            ohlc_frames[resolved] = df
            data_dict[resolved] = df[~df.index.duplicated(keep='last')]['Close']
        else:
            excluded_tickers.append({"ticker": t, "error": err or "No data returned."})

    if not data_dict:
        return {"error": "Could not fetch data for provided tickers.", "excluded_tickers": excluded_tickers}

    price_df = pd.DataFrame(data_dict).ffill().dropna()
    
    try:
        # Step 1: Optimize
        # NOTE: prices are each ticker's own LOCAL currency (USD for US
        # tickers, INR for .NS/.BO). A previous "USD normalization" step
        # divided Indian prices by a single spot FX rate, which cancels out
        # exactly in percentage-return terms (mu/S/backtests are unaffected
        # either way) -- it gave the appearance of modeling FX risk while
        # doing nothing. It has been removed; see `fx_note` in the result.
        opt_key = str(optimize_type or "mvo").strip().lower()
        returns = price_df.pct_change(fill_method=None).dropna()
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

            opt_results = run_markowitz_optimize(price_df)
            weights = opt_results["optimized_weights"]
        elif opt_key == "black_litterman":
            from pypfopt import EfficientFrontier
            from tools.optimization.black_litterman import optimize as run_black_litterman_optimize

            implied_views = None
            if not mu.empty:
                best_asset = str(mu.idxmax())
                implied_views = {best_asset: float(mu.loc[best_asset])}

            bl_res = run_black_litterman_optimize(price_df, views=implied_views)
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
        
        # Step 3: Institutional intelligence, blended across the WHOLE portfolio.
        # Previously only ONE ticker (whichever resolved first) drove every risk
        # field regardless of weights, so two users with the identical portfolio
        # in a different list order could get different, sometimes
        # contradictory, verdicts. Each held ticker is now analyzed on its own
        # and blended by portfolio weight (renormalized over tickers whose
        # analysis succeeded).
        per_ticker_intel, blended_intel = _compute_portfolio_intelligence(
            weights, ohlc_frames, _infer_benchmark_ticker
        )

        # A single representative ticker (highest-weighted with usable data) is
        # still surfaced for readability in `reasoning` and in the legacy
        # quant_analysis/alpha_analysis fields; all VERDICT MATH below uses the
        # portfolio-wide blend, not this one ticker.
        intel_ticker = None
        benchmark_ticker = None
        quant_analysis = None
        alpha_analysis = None
        if blended_intel:
            usable_entries = [e for e in per_ticker_intel if e["ticker"] in blended_intel["tickers_used"]]
            representative = max(usable_entries, key=lambda e: e["weight"])
            intel_ticker = representative["ticker"]
            benchmark_ticker = representative["benchmark"]
            quant_analysis = representative["quant_analysis"]
            alpha_analysis = representative["alpha_analysis"]

        # Step 4: Risk-adjusted verdicts, computed from the portfolio-wide blend.
        backtest_verdict = "STAY AWAY"
        if actual_sharpe > 1.2:
            backtest_verdict = "STRONG BUY"
        elif actual_sharpe > 0.7:
            backtest_verdict = "PROPER"

        alpha_value = blended_intel["alpha_annualized"] if blended_intel else None
        beta_value = blended_intel["beta"] if blended_intel else None
        r_squared = blended_intel["r_squared"] if blended_intel else None
        one_day_var_pct = blended_intel["one_day_var_95_pct"] if blended_intel else 0.0

        # A clearly bad backtest (non-finite or non-positive Sharpe) must be
        # able to surface as STAY AWAY. Previously this branch unconditionally
        # overwrote strategic_verdict with REDUCE/ACCUMULATE/NEUTRAL whenever
        # alpha was numeric -- true almost every call -- which made STAY AWAY
        # structurally unreachable even for a portfolio that lost money with a
        # deeply negative Sharpe (it would still show e.g. "NEUTRAL").
        if not math.isfinite(actual_sharpe) or actual_sharpe <= 0:
            strategic_verdict = "STAY AWAY"
        elif isinstance(alpha_value, (int, float)):
            if alpha_value < 0:
                strategic_verdict = "REDUCE"
            elif actual_sharpe >= 0.9 and alpha_value > 0.02:
                strategic_verdict = "ACCUMULATE"
            else:
                strategic_verdict = "NEUTRAL"
        else:
            strategic_verdict = backtest_verdict

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

        if blended_intel:
            reasoning += (
                f" Portfolio-weighted risk (blended across {blended_intel['tickers_used']}, "
                f"coverage {blended_intel['coverage_weight']*100:.0f}% of allocation): "
                f"Beta={blended_intel['beta']}, Alpha={blended_intel['alpha_annualized']*100:.2f}%, "
                f"R-squared={blended_intel['r_squared']}, VaR95={blended_intel['one_day_var_95_pct']:.2f}%, "
                f"dominant regime={blended_intel['dominant_regime']}."
            )
            if intel_ticker:
                reasoning += f" Representative single-name detail: {intel_ticker} vs {benchmark_ticker}."
        elif per_ticker_intel:
            reasoning += " Institutional intelligence unavailable: analysis failed for every held ticker."

        reasoning += (
            f" Estimated 95% one-day capital-at-risk on notional {amount} is {capital_at_risk:.2f}. "
            f"Capital plan: {capital_plan}."
        )

        if risk_flags:
            reasoning += " Risk flags: " + "; ".join(risk_flags) + "."

        if blended_intel and blended_intel.get("dominant_regime") == "MEAN_REVERTING":
            reasoning += " Regime filter: avoid pure trend-following entries while mean reversion dominates."

        res = {
            "requested_tickers": requested_tickers,
            "included_tickers": list(data_dict.keys()),
            "excluded_tickers": excluded_tickers,
            "fx_note": (
                "Prices are each ticker's own local currency (USD for US tickers, "
                "INR for .NS/.BO tickers); FX risk between markets is not modeled."
            ),
            "recommended_weights": weights,
            "portfolio_intelligence": {
                "per_ticker": per_ticker_intel,
                "blended": blended_intel,
            },
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
