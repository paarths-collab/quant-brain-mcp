import vectorbt as vbt

from tools.strategies._common import history_error, pct, positive_int, ratio


def run_strategy(df, fast=50, slow=200):
    """
    STRATEGY: Classic Moving Average Crossover.
    WHEN TO USE: In sustained trending markets.
    MARKET CONDITION: Best for Bull Runs. Avoid in Sideways/Choppy markets.
    RISK: High lag from slow moving averages.
    """
    fast, slow = positive_int("fast", fast), positive_int("slow", slow)
    if fast >= slow:
        return {"error": f"fast ({fast}) must be shorter than slow ({slow})."}
    close = df["Close"]
    error = history_error(close, slow + 1, "Trend Crossover")
    if error:
        return error
    fast_ma = vbt.MA.run(close, fast)
    slow_ma = vbt.MA.run(close, slow)

    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)

    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, init_cash=100000, freq="1D")
    stats = pf.stats()

    return {
        "strategy_name": "Trend Crossover",
        "win_rate": pct(stats['Win Rate [%]']),
        "sharpe_ratio": ratio(stats['Sharpe Ratio']),
        "max_drawdown": pct(stats['Max Drawdown [%]']),
        "profit_factor": ratio(stats['Profit Factor']),
        "total_trades": stats['Total Trades'],
        "total_return": pct(stats['Total Return [%]']),
    }
