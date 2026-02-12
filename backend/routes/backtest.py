import math
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse, Response
from backend.services.backtest_service import run_backtest_service, run_multi_strategy_backtest, generate_backtest_report, prepare_candles_df, run_backtest_on_df
from backend.services.strategies.strategy_adapter import STRATEGY_REGISTRY
from backend.services.market_data_service import fetch_candles
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import numpy as np

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


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
            "downloadUrl": f"/api/backtest/report/download/{filename}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
