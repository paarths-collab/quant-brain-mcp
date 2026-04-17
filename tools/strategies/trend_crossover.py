import vectorbt as vbt


def run_strategy(df, fast=50, slow=200):
    """
    STRATEGY: Classic Moving Average Crossover.
    WHEN TO USE: In sustained trending markets.
    MARKET CONDITION: Best for Bull Runs. Avoid in Sideways/Choppy markets.
    RISK: High lag from slow moving averages.
    """
    close = df["Close"]
    fast_ma = vbt.MA.run(close, fast)
    slow_ma = vbt.MA.run(close, slow)

    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)

    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, init_cash=100000)
    stats = pf.stats()

    return {
        "strategy_name": "SMA Crossover",
        "win_rate": f"{stats['Win Rate [%]']:.2f}%",
        "sharpe_ratio": round(stats['Sharpe Ratio'], 2),
        "max_drawdown": f"{stats['Max Drawdown [%]']:.2f}%",
        "profit_factor": round(stats['Profit Factor'], 2),
        "total_trades": stats['Total Trades'],
        "total_return": f"{stats['Total Return [%]']:.2f}%",
    }
