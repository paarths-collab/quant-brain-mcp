# services/runner.py

from backend.services.data_loader import get_data
from backend.services.strategy_registry import get_strategy
from backend.services.backtest_engine import run_backtest
from backend.services.metrics import calculate_metrics

def run_strategy(
    strategy_name,
    ticker,
    start_date,
    end_date,
    market,
    initial_capital=100_000,
    **strategy_params
):
    data = get_data(ticker, start_date, end_date, market)
    if data.empty:
        return {"error": "No data found"}

    strategy = get_strategy(strategy_name, **strategy_params)
    signals = strategy.generate_signals(data)

    equity_df, trades = run_backtest(signals, initial_capital)
    metrics = calculate_metrics(equity_df, trades, initial_capital)

    return {
        "strategy": strategy.name,
        "parameters": strategy.parameters(),
        "metrics": metrics,
        "equity": equity_df,
        "trades": trades,
        "signals": signals,
    }
