import math
from fastapi import APIRouter, HTTPException, Body, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from .service import run_backtest_service, run_multi_strategy_backtest, generate_backtest_report, prepare_candles_df, run_backtest_on_df
from .core.groq_agent import GroqAgent
from .core.strategy_adapter import STRATEGY_REGISTRY
from .core.market_data_service import fetch_candles
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import numpy as np
import json
import asyncio
import os

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


@router.post("/interpret")
def interpret_backtest(payload: Dict[str, Any] = Body(...)):
    """
    Explain backtest outputs using Groq with research analyst perspective.
    Expects detailed summary payload from frontend including equity stats and trade analysis.
    """
    symbol = payload.get("symbol")
    market = payload.get("market", "US")
    selected_strategies = payload.get("selectedStrategies", [])
    summary = payload.get("summary", {})

    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
    if not isinstance(summary, dict) or not summary:
        raise HTTPException(status_code=400, detail="summary payload is required")

    # Build comprehensive institutional research analyst prompt
    prompt = (
        "You are a professional quantitative research analyst with institutional trading experience. "
        "Produce a detailed, comprehensive research report on this backtest result. "
        "Write as if this will be reviewed by portfolio managers and risk officers.\n\n"
        
        "REPORT STRUCTURE (follow exactly):\n\n"
        
        "## EXECUTIVE SUMMARY & RECOMMENDATION\n"
        "Begin with a clear VERDICT: [BUY/SELL/HOLD]\n"
        "Provide 2-3 sentences explaining the recommendation with specific metrics that support it.\n"
        "Include the key thesis: why this strategy works (or doesn't).\n\n"
        
        "## EQUITY CURVE ANALYSIS (DETAILED)\n"
        "- Describe the complete trajectory: Is growth monotonic, volatile, recovering from drawdown?\n"
        "- Identify all major inflection points and what caused them\n"
        "- Comment on acceleration/deceleration: Is the strategy gaining or losing momentum?\n"
        "- Regime analysis: How does performance vary across market conditions (bull/bear/ranging)?\n"
        "- Recovery patterns: After major drawdowns, does recovery happen quickly or slowly?\n"
        "- Consistency: Are returns steady or lumpy? What does this tell us about the strategy's nature?\n\n"
        
        "## RISK & CAPITAL PRESERVATION ASSESSMENT\n"
        "- Maximum Drawdown Context: What does [X]% drawdown mean practically? (e.g., '40% = lost $40k on $100k capital')\n"
        "  * How long did recovery take? What was the intra-recovery volatility?\n"
        "  * Worst case recovery trajectory: how many periods to get back to the peak?\n"
        "- Volatility Analysis: Annualized volatility and what it means (compare: S&P 500 ~15-18%)\n"
        "- Tail Risk (Monte Carlo): If available:\n"
        "  * Interpret P5 (5th percentile - worst-case scenario): What is the potential loss in the downside tail?\n"
        "  * Compare P50 (median) to P95 (optimistic): how wide is this band relative to capital?\n"
        "  * Trend of the Monte Carlo fan: Is it tightening (more predictable) or widening (more uncertain)?\n"
        "- Risk-to-Return Ratio: Are returns proportional to the risk taken? (Rule: need 2-3% return per 1% drawdown risk)\n\n"
        
        "## TRADE EXECUTION QUALITY\n"
        "- Win Rate Context: [X]% means [Y] wins per [Z] losses. How does this compare to market dynamics?\n"
        "  * Is this sustainable or regime-dependent?\n"
        "- Trade Size Consistency: Are wins significantly larger than losses? (Profit Factor = sum wins / sum losses)\n"
        "  * Analyze: Average win vs Average loss (3:1 ratio is strong, 1:1 is weak)\n"
        "- Trade Expectancy: Expected P&L per trade = (Win% × Avg Win) - (Loss% × Avg Loss)\n"
        "  * Is this positive? By how much? Is it economically viable after costs?\n"
        "- Trading Frequency: [X] trades total. Is this over/under exposed? (too many = curve-fitting, too few = inefficient)\n"
        "- Trade Clustering: Do winners/losers cluster in time periods or are they distributed?\n"
        "  * Clustering = strategy may be regime-dependent (dangerous)\n\n"
        
        "## RETURN QUALITY & EFFICIENCY METRICS\n"
        "- Total Return [X]%: In context of the [Y] period tested, is this beating/lagging benchmarks?\n"
        "- Sharpe Ratio [X]: What does this mean?\n"
        "  * <0.5 = Poor (barely compensating for risk)\n"
        "  * 0.5-1.0 = Acceptable (decent risk-adjusted returns)\n"
        "  * 1.0-2.0 = Good (well-rewarded for risk)\n"
        "  * >2.0 = Excellent (institutional-grade performance)\n"
        "- Sortino Ratio [if available]: Same as Sharpe but only penalizes downside volatility (more relevant)\n"
        "- Return Consistency: Smooth returns or inconsistent performance?\n\n"
        
        "## STRATEGY VIABILITY & ROBUSTNESS\n"
        "- Economic Viability: After accounting for\n"
        "  * Spreads/slippage (0.1-0.5% per trade)\n"
        "  * Commission (0.01-0.1% per side)\n"
        "  * Market impact on larger accounts\n"
        "  ...is the strategy still profitable?\n"
        "- Overfitting Detection: Are there signs the strategy is curve-fitted to this data?\n"
        "  * Look for: Short-term parameter optimization, too many rules, perfect precision on trades\n"
        "- Robustness: Does this work in multiple market regimes or just this specific period?\n"
        "- Parameter Sensitivity: Are results stable or do they change dramatically with parameter tweaks?\n"
        "- Market Regime Dependency:\n"
        "  * Is the strategy momentum-based, mean-reversion, or volatility-driven?\n"
        "  * What happened in strong trends vs choppy sideways markets?\n\n"
        
        "## CRITICAL RISKS & RED FLAGS\n"
        "List 2-3 specific risks that could cause this strategy to fail:\n"
        "- [Risk 1 with concrete example]\n"
        "- [Risk 2 with concrete example]\n"
        "- [Risk 3 with concrete example]\n\n"
        
        "## STRATEGIC STRENGTHS & OPPORTUNITIES\n"
        "List 2-3 specific strengths that make this strategy valuable:\n"
        "- [Strength 1 with concrete metrics]\n"
        "- [Strength 2 with concrete metrics]\n"
        "- [Strength 3 with concrete metrics]\n\n"
        
        "## VALIDATION & DEPLOYMENT ROADMAP\n"
        "1. IMMEDIATE PRIORITY: [Most critical next step - e.g., walk-forward test, out-of-sample validation]\n"
        "2. RISK CONTROLS: [Specific position sizing, stop-loss, or portfolio constraints]\n"
        "3. LIVE MONITORING: [What metrics to track in production? What would trigger pausing the strategy?]\n"
        "4. OPTIMIZATION: [If any parameter tuning is needed before deployment]\n\n"
        
        "ANALYSIS RULES:\n"
        "- Use specific numbers from the data. NO vague statements.\n"
        "- Assume the reader is a professional trader/PM - be direct and honest.\n"
        "- Point out both strengths AND weaknesses with equal intensity.\n"
        "- Compare to institutional benchmarks (Sharpe 1.0+ is competitive).\n"
        "- Do not be diplomatic - state explicitly if the strategy has fatal flaws.\n"
        "- Length: 800-1500 words. Prioritize depth over brevity.\n\n"
        
        f"BACKTEST DATA:\n"
        f"Asset: {symbol} ({market})\n"
        f"Period: {summary.get('range', 'N/A')}\n"
        f"Candle Interval: {summary.get('interval', 'N/A')}\n"
        f"Full Data: {json.dumps(summary, indent=2, default=str)}"
    )

    llm = GroqAgent()
    analysis = llm.generate_response(prompt=prompt, model="llama-3.3-70b-versatile", temperature=0.3)
    if not analysis or analysis.lower().startswith("error"):
        raise HTTPException(status_code=502, detail="AI interpretation failed. Check GROQ_API_KEY and try again.")

    return {"analysis": analysis}


@router.post("/interpret-image")
def interpret_backtest_image(payload: Dict[str, Any] = Body(...)):
    """Explain backtest charts from screenshot image using Groq vision with research analyst perspective."""
    symbol = payload.get("symbol")
    market = payload.get("market", "US")
    selected_strategies = payload.get("selectedStrategies", [])
    image_data_url = payload.get("imageDataUrl")
    context = payload.get("context", {})

    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
    if not image_data_url:
        raise HTTPException(status_code=400, detail="imageDataUrl is required")

    prompt = (
        "You are a professional quantitative research analyst reviewing a backtest dashboard screenshot. "
        "Extract all visible information and produce a detailed, comprehensive research assessment.\n\n"
        
        "ANALYSIS STRUCTURE:\n\n"
        
        "## EXECUTIVE SUMMARY & RECOMMENDATION\n"
        "Start with a clear VERDICT: [BUY/SELL/HOLD]\n"
        "Provide 2-3 sentences of reasoning based on visible metrics.\n"
        "State the key thesis based on what you see in the charts.\n\n"
        
        "## EQUITY CURVE ANALYSIS (FROM CHART)\n"
        "Describe the complete visual story of the equity curve:\n"
        "- Overall trajectory: Is it monotonically increasing, volatile with recoveries, or declining?\n"
        "- Growth pattern: Smooth, choppy, accelerating, or decelerating?\n"
        "- Visible inflection points: Where did major directional changes occur?\n"
        "- Recovery behavior: After visible dips, does it bounce back quickly or slowly?\n"
        "- Recent performance: Is the curve trending up or showing signs of weakness at the end?\n"
        "- Cumulative growth: Trace the path from start to end value\n\n"
        
        "## RISK & DRAWDOWN ASSESSMENT\n"
        "Analyze the visible drawdown metrics:\n"
        "- Maximum Drawdown [read exact value]: What percentage of capital was lost at worst?\n"
        "  * Context: [X]% drawdown means on $100k, you'd be down to $[remaining]\n"
        "- Drawdown Duration: Can you estimate how long it took to recover from the deepest point?\n"
        "- Drawdown Frequency: Are there multiple significant drawdowns or just one large one?\n"
        "- Recovery Path: Does recovery appear V-shaped (quick) or L-shaped (slow and painful)?\n"
        "- Underwater Analysis: What percentage of the backtest period was the strategy underwater (negative)?\n"
        "- Volatility from chart shape: Is the equity curve smooth (low volatility) or jagged (high volatility)?\n\n"
        
        "## MONTE CARLO RISK VISUALIZATION (IF CHART VISIBLE)\n"
        "If Monte Carlo fan chart is visible, analyze:\n"
        "- P50 (Median Path): Is the center line trending up or down?\n"
        "- P5 vs P95 Spread: How wide is the fan? Narrow = consistent, wide = risky\n"
        "- Tail Risk (P5): How bad is the worst-case scenario shown?\n"
        "- Upside (P95): How much upside is the strategy capable of in favorable conditions?\n"
        "- Fan Evolution: Is the fan tightening (confidence) or widening (uncertainty) over time?\n"
        "- Median vs Best Case: Big gap or small? What does this suggest about strategy consistency?\n\n"
        
        "## PERFORMANCE METRICS (READ FROM DASHBOARD)\n"
        "For each metric visible, provide both the number AND interpretation:\n"
        "- Total Return [X%]: In context of the test period, is this good/bad/expected?\n"
        "- Sharpe Ratio [X]: What does this mean?\n"
        "  * <0.5 = Poor; 0.5-1.0 = Acceptable; 1.0-2.0 = Good; >2.0 = Excellent\n"
        "- Sortino Ratio [if visible]: Downside-focused risk metric (more relevant than Sharpe)\n"
        "- Win Rate [X%]: Does this seem sustainable or dependent on specific conditions?\n"
        "- Profit Factor [X]: Ratio of wins to losses\n"
        "  * <1.0 = Losing strategy; 1.0-1.5 = Weak; 1.5-2.0 = Good; >2.0 = Excellent\n"
        "- Trade Count: How many trades generated these results? Many = over-trading risk, Few = inefficient\n\n"
        
        "## TRADE DISTRIBUTION ANALYSIS (IF VISIBLE)\n"
        "If trade markers or logs are visible:\n"
        "- Trade Frequency: How often is the strategy trading? (frequency visible from dots/marks)\n"
        "- Win/Loss Clustering: Do winners and losers cluster in time or spread evenly?\n"
        "- Trade Sizing: Can you tell if position size stayed constant or varied?\n"
        "- Losing Streaks: Are there visible periods of consecutive losses?\n"
        "- Winning Periods: Are gains concentrated in specific bull markets or distributed?\n\n"
        
        "## CRITICAL RED FLAGS (VISIBLE CONCERNS)\n"
        "List 2-3 specific issues visible in the dashboard:\n"
        "1. [Concern 1]: [Be specific about what you see in the chart]\n"
        "2. [Concern 2]: [Specific observation from metrics]\n"
        "3. [Concern 3]: [What the data shows]\n\n"
        
        "## GREEN FLAGS (VISIBLE STRENGTHS)\n"
        "List 2-3 specific positives visible in the dashboard:\n"
        "1. [Strength 1]: [Concrete metric from chart]\n"
        "2. [Strength 2]: [Observable pattern]\n"
        "3. [Strength 3]: [Data point]\n\n"
        
        "## IMMEDIATE ASSESSMENT\n"
        "Based on what's visible:\n"
        "- Is this strategy showing institutional-grade quality metrics?\n"
        "- What is the biggest concern for live trading?\n"
        "- What validation step is needed before deployment?\n"
        "- Risk/Reward Ratio: Are returns proportional to risks taken?\n\n"
        
        "CRITICAL RULES:\n"
        "- Read EXACT values from the dashboard - if you cannot read a value, explicitly state 'value not visible'\n"
        "- Never guess or estimate values that you cannot see clearly\n"
        "- Be specific and cite exact numbers from the visible metrics\n"
        "- Compare metrics to professional standards (Sharpe 1.0+, win rate 50%+, profit factor 1.5+)\n"
        "- Point out contradictions (e.g., good return but high drawdown)\n"
        "- Do not be polite - state if the strategy shows red flags\n"
        "- Length: 800-1200 words. Detailed analysis prioritized over brevity.\n\n"
        
        f"Asset: {symbol} ({market})\n"
        f"Test Period: {context.get('range', 'N/A')}\n"
        f"Interval: {context.get('interval', 'N/A')}\n"
        f"Test Mode: {context.get('mode', 'N/A')}\n"
        f"Strategies Tested: {', '.join(selected_strategies)}"
    )

    llm = GroqAgent()
    requested_model = payload.get("imageModel") or os.getenv("GROQ_VISION_MODEL") or "meta-llama/llama-4-scout-17b-16e-instruct"
    candidate_models = [
        requested_model,
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.2-11b-vision-preview",
    ]

    analysis = ""
    last_error = ""
    used_model = ""
    for model_name in dict.fromkeys(candidate_models):
        used_model = model_name
        analysis = llm.generate_vision_response(
            prompt=prompt,
            image_data_url=image_data_url,
            model=model_name,
            temperature=0.2,
        )
        if analysis and not analysis.lower().startswith("error"):
            break
        last_error = analysis or "Unknown model failure"

    if not analysis or analysis.lower().startswith("error"):
        raise HTTPException(
            status_code=502,
            detail=f"AI image interpretation failed. Last model tried: {used_model}. Error: {last_error}",
        )

    return {"analysis": analysis, "model": used_model}


@router.websocket("/ws")
async def backtest_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time backtest updates.
    Client sends: {"symbol": "AAPL", "strategy": "ema_crossover", "range": "1y", "params": {...}}
    Server sends progress updates and final result.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            symbol = payload.get("symbol")
            if not symbol:
                await websocket.send_json({"error": "Symbol is required"})
                continue
            
            # Send starting notification
            await websocket.send_json({
                "status": "starting",
                "message": f"Running backtest for {symbol}..."
            })
            
            # Run backtest in thread pool to avoid blocking
            try:
                strategy = payload.get("strategy") or payload.get("strategies", [None])[0]
                if not strategy:
                    await websocket.send_json({"error": "Strategy is required"})
                    continue
                
                # Send data fetching status
                await websocket.send_json({
                    "status": "fetching",
                    "message": "Fetching market data..."
                })
                
                # Run backtest
                result = await asyncio.to_thread(
                    run_backtest_service,
                    symbol=symbol,
                    strategy_name=strategy,
                    range_period=payload.get("range", "1y"),
                    interval=payload.get("interval", "1d"),
                    market=payload.get("market", "us"),
                    start_date=payload.get("start"),
                    end_date=payload.get("end"),
                    **payload.get("params", {})
                )
                
                if "error" in result:
                    await websocket.send_json({"error": result["error"]})
                else:
                    # Send progress update
                    await websocket.send_json({
                        "status": "processing",
                        "message": "Calculating metrics..."
                    })
                    
                    # Send final result
                    await websocket.send_json({
                        "status": "complete",
                        "data": _sanitize_floats(result)
                    })
                    
            except Exception as e:
                await websocket.send_json({
                    "status": "error",
                    "error": str(e)
                })
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass


def _sanitize_floats(obj):
    """Recursively replace inf/nan floats with None for JSON safety."""
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_floats(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


@router.post("/run")
def run_simulation(
    payload: Dict[str, Any] = Body(...)
):
    """
    Runs a backtest simulation with single or multiple strategies.
    
    Single strategy payload:
    {
        "symbol": "AAPL",
        "strategy": "ema_crossover",
        "range": "1y",
        "params": {"fast": 20, "slow": 50}
    }
    
    Multiple strategies payload:
    {
        "symbol": "AAPL",
        "strategies": ["ema_crossover", "momentum", "rsi_strategy"],
        "range": "1y",
        "params": {
            "ema_crossover": {"fast": 12, "slow": 26},
            "momentum": {"lookback_period": 20},
            "rsi_strategy": {"rsi_period": 14, "oversold": 30, "overbought": 70}
        }
    }
    """
    try:
        symbol = payload.get("symbol")
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")
        
        range_period = payload.get("range", "1y")
        interval = payload.get("interval", "1d")
        market = payload.get("market", "us")
        start_date = payload.get("start")
        end_date = payload.get("end")
        
        # Check for multiple strategies
        strategies = payload.get("strategies")
        
        if strategies and isinstance(strategies, list) and len(strategies) > 1:
            # Multiple strategies mode
            params_dict = payload.get("params", {})
            
            result = run_multi_strategy_backtest(
                symbol=symbol,
                strategy_names=strategies,
                range_period=range_period,
                interval=interval,
                market=market,
                start_date=start_date,
                end_date=end_date,
                params_dict=params_dict
            )
        else:
            # Single strategy mode (backward compatible)
            strategy = payload.get("strategy") or (strategies[0] if strategies else None)
            if not strategy:
                raise HTTPException(status_code=400, detail="Strategy is required")
                
            params = payload.get("params", {})
            # If params is a dict of strategy params, extract the right one
            if isinstance(params, dict) and strategy in params:
                params = params[strategy]
            
            result = run_backtest_service(
                symbol=symbol,
                strategy_name=strategy,
                range_period=range_period,
                interval=interval,
                market=market,
                start_date=start_date,
                end_date=end_date,
                **params
            )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return _sanitize_floats(result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
def get_available_strategies():
    """
    Returns list of available backtest strategies with their parameters.
    """
    descriptions = {
        "momentum": "Buy stocks with strong price momentum",
        "mean_reversion": "Trade based on deviation from moving average",
        "ema_crossover": "Golden/Death cross using EMAs",
        "sma_crossover": "Golden/Death cross using SMAs",
        "macd": "Trade on MACD line crossing signal line",
        "rsi_reversal": "Buy oversold, sell overbought based on RSI",
        "rsi_momentum": "RSI with trend confirmation filter",
        "breakout": "Trade breakouts from recent ranges",
        "fibonacci_pullback": "Pullback entries around Fib retracements",
        "pairs_trading": "Mean reversion between correlated pairs",
        "support_resistance": "Trades around support/resistance zones",
        "channel_trading": "Trades within price channels",
    }

    strategies = []
    for strategy_id, strategy_cls in STRATEGY_REGISTRY.items():
        try:
            params = strategy_cls().parameters()
        except Exception:
            params = {}
        name = getattr(strategy_cls, "name", strategy_id.replace("_", " ").title())
        strategies.append({
            "id": strategy_id,
            "name": name,
            "description": descriptions.get(strategy_id, "Technical trading strategy"),
            "params": params
        })

    return {
        "strategies": strategies
    }


@router.post("/heatmap")
def run_heatmap(payload: Dict[str, Any] = Body(...)):
    """
    Generate a strategy performance heatmap for a parameter grid.
    Payload:
    {
        "symbol": "AAPL",
        "strategy": "ema_crossover",
        "range": "1y"
    }
    """
    try:
        symbol = payload.get("symbol")
        strategy = payload.get("strategy")
        if not symbol or not strategy:
            raise HTTPException(status_code=400, detail="Symbol and strategy are required")

        range_period = payload.get("range", "1y")

        heatmap_config = {
            "ema_crossover": {
                "param_x": "fast",
                "x_values": [5, 8, 12, 16, 20],
                "param_y": "slow",
                "y_values": [30, 50, 70, 100, 150],
            },
            "mean_reversion": {
                "param_x": "window",
                "x_values": [10, 20, 30, 40, 50],
                "param_y": "num_std",
                "y_values": [1.5, 2.0, 2.5, 3.0],
            },
            "macd": {
                "param_x": "fast",
                "x_values": [6, 12, 16],
                "param_y": "slow",
                "y_values": [26, 40, 60],
            },
            "rsi_reversal": {
                "param_x": "lower",
                "x_values": [20, 30, 40],
                "param_y": "upper",
                "y_values": [60, 70, 80],
            },
            "sma_crossover": {
                "param_x": "short_window",
                "x_values": [20, 50, 100],
                "param_y": "long_window",
                "y_values": [100, 150, 200],
            },
            "rsi_momentum": {
                "param_x": "rsi_window",
                "x_values": [10, 14, 21],
                "param_y": "lower",
                "y_values": [30, 40, 50],
            },
            "support_resistance": {
                "param_x": "lookback",
                "x_values": [20, 30, 50],
                "param_y": "tolerance_pct",
                "y_values": [0.01, 0.02, 0.03],
            },
        }

        config = heatmap_config.get(strategy)
        if not config:
            raise HTTPException(status_code=400, detail="Heatmap not supported for this strategy")

        param_x = payload.get("param_x", config["param_x"])
        param_y = payload.get("param_y", config["param_y"])
        x_values = payload.get("x_values", config["x_values"])
        y_values = payload.get("y_values", config["y_values"])

        candles = fetch_candles(symbol, "1d", range_period)
        if not candles:
            raise HTTPException(status_code=400, detail="No data found for heatmap")

        df = prepare_candles_df(candles)
        values = []

        for y in y_values:
            row = []
            for x in x_values:
                params = {param_x: x, param_y: y}

                if strategy in ["ema_crossover", "macd"]:
                    if params.get("fast") >= params.get("slow"):
                        row.append(None)
                        continue
                if strategy == "rsi_reversal" and params.get("lower") >= params.get("upper"):
                    row.append(None)
                    continue

                try:
                    res_df = run_backtest_on_df(df, strategy, **params)
                    total_return = ((res_df['equity'].iloc[-1] - 100000) / 100000) * 100
                    row.append(round(float(total_return), 2))
                except Exception:
                    row.append(None)
            values.append(row)

        return {
            "symbol": symbol,
            "strategy": strategy,
            "paramX": param_x,
            "paramY": param_y,
            "xValues": x_values,
            "yValues": y_values,
            "values": values,
            "metric": "totalReturn"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report")
def generate_report(payload: Dict[str, Any] = Body(...)):
    """
    Generates a downloadable backtest report (HTML/CSV).
    
    Payload:
    {
        "symbol": "AAPL",
        "strategies": ["ema_crossover", "momentum"],
        "results": { ... backtest results from /run ... },
        "format": "html" | "csv"
    }
    """
    try:
        symbol = payload.get("symbol", "UNKNOWN")
        strategies = payload.get("strategies", [])
        results = payload.get("results", {})
        report_format = payload.get("format", "html")
        
        report = generate_backtest_report(
            symbol=symbol,
            strategies=strategies,
            results=results,
            report_format=report_format
        )
        
        if report.get("error"):
            raise HTTPException(status_code=500, detail=report["error"])
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/download/{filename}")
def download_report(filename: str):
    """
    Downloads a generated backtest report file.
    """
    from pathlib import Path
    
    reports_dir = Path(__file__).parent.parent / "reports"
    file_path = reports_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    if filename.endswith(".html"):
        media_type = "text/html"
    elif filename.endswith(".pdf"):
        media_type = "application/pdf"
    else:
        media_type = "text/csv"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )


@router.post("/quantstats-report")
def generate_quantstats_report(payload: Dict[str, Any] = Body(...)):
    """
    Generate a QuantStats HTML report for a backtest.

    Payload:
    {
        "symbol": "AAPL",
        "strategy": "ema_crossover",
        "range": "1y",
        "params": {"fast": 12, "slow": 26},
        "benchmark": "SPY"
    }
    """
    import quantstats as qs
    import pandas as pd

    symbol = payload.get("symbol")
    strategy_name = payload.get("strategy")
    if not symbol or not strategy_name:
        raise HTTPException(status_code=400, detail="symbol and strategy are required")

    range_period = payload.get("range", "1y")
    params = payload.get("params", {})
    benchmark = payload.get("benchmark", "SPY")

    try:
        # 1. Fetch candles and prepare DataFrame
        candles = fetch_candles(symbol, "1d", range_period)
        if not candles:
            raise HTTPException(status_code=400, detail="No market data found")

        df = prepare_candles_df(candles)

        # 2. Run backtest to get strategy returns
        res_df = run_backtest_on_df(df, strategy_name, initial_capital=100000, **params)

        # 3. Extract daily strategy returns as a proper pandas Series
        returns = res_df["strategy_returns"].copy()
        returns.index = pd.to_datetime(res_df["Date"])
        returns.name = f"{strategy_name} ({symbol})"

        # Drop NaN/inf values
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()

        if returns.empty or len(returns) < 5:
            raise HTTPException(status_code=400, detail="Not enough return data to generate report")

        # 4. Generate QuantStats HTML report
        safe_symbol = symbol.replace(".", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"quantstats_{safe_symbol}_{strategy_name}_{timestamp}.html"
        filepath = REPORTS_DIR / filename

        qs.reports.html(
            returns,
            benchmark=benchmark,
            output=str(filepath),
            title=f"{strategy_name.replace('_', ' ').title()} — {symbol}",
            download_filename=filename,
        )

        return {
            "success": True,
            "filename": filename,
            "downloadUrl": f"/backtest/report/download/{filename}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
