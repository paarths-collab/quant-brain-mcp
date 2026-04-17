import vectorbt as vbt


def run_backtest(df, fast=12, slow=26, signal=9):
    """Vectorized backtest for MACD trend following."""
    macd = vbt.MACD.run(df["Close"], fast=fast, slow=slow, signal=signal)
    entries = macd.macd_crossed_above(macd.signal)
    exits = macd.macd_crossed_below(macd.signal)

    pf = vbt.Portfolio.from_signals(df["Close"], entries, exits, fees=0.001)
    stats = pf.stats()

    return {
        "strategy_name": "MACD Momentum",
        "total_return": f"{stats['Total Return [%]']:.2f}%",
        "sharpe_ratio": round(stats['Sharpe Ratio'], 2),
        "win_rate": f"{stats['Win Rate [%]']:.2f}%",
        "max_drawdown": f"{stats['Max Drawdown [%]']:.2f}%",
        "total_trades": stats['Total Trades'],
    }
