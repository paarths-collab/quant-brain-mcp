from __future__ import annotations

from typing import Any, Dict, Optional

# BacktestAgent stub
class BacktestAgent:
    def analyze(*a, **k): return {}
    def run(*a, **k): return {}


def run_backtest_agent(
    symbol: str,
    strategy: str,
    range_period: str = "1y",
    params: Optional[Dict[str, Any]] = None,
    run_backtest: bool = True,
) -> Dict[str, Any]:
    """
    Service wrapper for the BacktestAgent.
    Returns a consistent response shape for API usage.
    """
    agent = BacktestAgent()
    return agent.analyze(
        symbol=symbol,
        strategy=strategy,
        range_period=range_period,
        params=params,
        run_backtest=run_backtest,
    )

