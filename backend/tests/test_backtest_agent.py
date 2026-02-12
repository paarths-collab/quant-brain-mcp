import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.agents.backtest_agent import BacktestAgent
from backend.services.backtest_agent_service import run_backtest_agent


def test_backtest_agent_stub():
    agent = BacktestAgent()
    result = agent.analyze(
        symbol="AAPL",
        strategy="ema_crossover",
        range_period="6mo",
        params={"fast": 12, "slow": 26},
        run_backtest=False,
    )

    assert result["status"] == "skipped"
    assert result["mode"] == "strategy_backtest"


def test_backtest_agent_service_stub():
    result = run_backtest_agent(
        symbol="AAPL",
        strategy="ema_crossover",
        range_period="6mo",
        params={"fast": 12, "slow": 26},
        run_backtest=False,
    )

    assert result["status"] == "skipped"
