import vectorbt as vbt


def run_crossover_backtest(df, fast=50, slow=200):
    """
    STRATEGY: Golden Cross (Fast crosses above Slow).
    WHEN TO USE: Identifying major trend shifts in Indian/US Bluechips.
    VERDICT: High Win Rate = Strong Trend. Low Win Rate = Choppy Market.
    """
    close = df["Close"]
    fast_ma = vbt.MA.run(close, fast)
    slow_ma = vbt.MA.run(close, slow)

    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)

    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001)
    stats = pf.stats()

    return {
        "total_return": f"{stats['Total Return [%]']:.2f}%",
        "win_rate": f"{stats['Win Rate [%]']:.2f}%",
        "sharpe": round(stats['Sharpe Ratio'], 2),
        "max_drawdown": f"{stats['Max Drawdown [%]']:.2f}%",
        "total_trades": stats["Total Trades"],
    }
