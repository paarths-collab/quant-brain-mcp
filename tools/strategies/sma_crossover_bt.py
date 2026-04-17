import vectorbt as vbt


def run_backtest(df, fast=50, slow=200):
    """Vectorized backtest for SMA Crossover."""
    fast_ma = vbt.MA.run(df["Close"], fast)
    slow_ma = vbt.MA.run(df["Close"], slow)

    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)

    pf = vbt.Portfolio.from_signals(df["Close"], entries, exits, fees=0.001)
    stats = pf.stats()

    return {
        "strategy_name": "SMA Crossover",
        "total_return": f"{stats['Total Return [%]']:.2f}%",
        "sharpe_ratio": round(stats['Sharpe Ratio'], 2),
        "win_rate": f"{stats['Win Rate [%]']:.2f}%",
        "max_drawdown": f"{stats['Max Drawdown [%]']:.2f}%",
        "profit_factor": round(stats['Profit Factor'], 2),
        "total_trades": stats['Total Trades'],
    }
