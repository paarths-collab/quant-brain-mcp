from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services.backtest_service import run_backtest_service


class BacktestAgent:
    """
    Backtest Agent (skeleton).

    Purpose: run fast, repeatable backtests for decision calibration.
    This is not a prediction engine.
    """

    def __init__(self, runner=None) -> None:
        self._runner = runner or run_backtest_service

    def analyze(
        self,
        symbol: str,
        strategy: str,
        range_period: str = "1y",
        params: Optional[Dict[str, Any]] = None,
        run_backtest: bool = True,
    ) -> Dict[str, Any]:
        params = params or {}

        if not run_backtest:
            return {
                "mode": "strategy_backtest",
                "symbol": symbol,
                "strategy": strategy,
                "range": range_period,
                "status": "skipped",
                "note": "Backtest execution disabled (run_backtest=false).",
            }

        result = self._runner(
            symbol=symbol,
            strategy_name=strategy,
            range_period=range_period,
            **params,
        )

        if "error" in result:
            return {
                "mode": "strategy_backtest",
                "symbol": symbol,
                "strategy": strategy,
                "range": range_period,
                "status": "error",
                "error": result["error"],
            }

        return {
            "mode": "strategy_backtest",
            "symbol": symbol,
            "strategy": strategy,
            "range": range_period,
            "status": "ok",
            "metrics": result.get("metrics", {}),
            "equity_curve": result.get("equity_curve", []),
            "trades": result.get("trades", []),
        }
