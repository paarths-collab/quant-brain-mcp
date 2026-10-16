import vectorbt as vbt

from tools.strategies._common import history_error, pct, positive_int, ratio


def run_backtest(df, fast=50, slow=200):
    """Vectorized backtest for SMA Crossover."""
    fast, slow = positive_int("fast", fast), positive_int("slow", slow)
    if fast >= slow:
        return {"error": f"fast ({fast}) must be shorter than slow ({slow})."}
    error = history_error(df["Close"], slow + 1, "SMA Crossover")
    if error:
        return error
    fast_ma = vbt.MA.run(df["Close"], fast)
    slow_ma = vbt.MA.run(df["Close"], slow)

    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)

    pf = vbt.Portfolio.from_signals(df["Close"], entries, exits, fees=0.001, freq="1D")
    stats = pf.stats()

    return {
        "strategy_name": "SMA Crossover",
        "total_return": pct(stats['Total Return [%]']),
        "sharpe_ratio": ratio(stats['Sharpe Ratio']),
        "win_rate": pct(stats['Win Rate [%]']),
        "max_drawdown": pct(stats['Max Drawdown [%]']),
        "profit_factor": ratio(stats['Profit Factor']),
        "total_trades": stats['Total Trades'],
    }
