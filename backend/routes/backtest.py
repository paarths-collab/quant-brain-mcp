from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse, Response
from backend.services.backtest_service import run_backtest_service, run_multi_strategy_backtest, generate_backtest_report
from typing import Dict, Any, List
from datetime import datetime

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])

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
        
        # Check for multiple strategies
        strategies = payload.get("strategies")
        
        if strategies and isinstance(strategies, list) and len(strategies) > 1:
            # Multiple strategies mode
            params_dict = payload.get("params", {})
            
            result = run_multi_strategy_backtest(
                symbol=symbol,
                strategy_names=strategies,
                range_period=range_period,
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
                **params
            )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
def get_available_strategies():
    """
    Returns list of available backtest strategies with their parameters.
    """
    return {
        "strategies": [
            {
                "id": "momentum",
                "name": "Momentum Strategy",
                "description": "Buy stocks with strong price momentum",
                "params": {"lookback_period": 20, "threshold": 0.05}
            },
            {
                "id": "mean_reversion",
                "name": "Mean Reversion",
                "description": "Trade based on price deviation from moving average",
                "params": {"ma_period": 20, "std_multiplier": 2}
            },
            {
                "id": "ema_crossover",
                "name": "EMA Crossover",
                "description": "Golden/Death cross using exponential moving averages",
                "params": {"fast": 12, "slow": 26}
            },
            {
                "id": "rsi_strategy",
                "name": "RSI Strategy",
                "description": "Buy oversold, sell overbought based on RSI levels",
                "params": {"rsi_period": 14, "oversold": 30, "overbought": 70}
            },
            {
                "id": "bollinger",
                "name": "Bollinger Bands",
                "description": "Trade based on price touching Bollinger bands",
                "params": {"bb_period": 20, "std_dev": 2}
            },
            {
                "id": "macd",
                "name": "MACD Strategy",
                "description": "Trade on MACD line crossing signal line",
                "params": {"fast": 12, "slow": 26, "signal": 9}
            }
        ]
    }


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
    
    media_type = "text/html" if filename.endswith(".html") else "text/csv"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )
