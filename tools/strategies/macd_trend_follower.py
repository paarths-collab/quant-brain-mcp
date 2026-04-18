import vectorbt as vbt
import pandas_ta as ta


def run_backtest(df, fast=12, slow=26, signal=9):
    """Vectorized backtest for MACD trend following."""
    close = df["Close"].astype(float)
    macd = ta.macd(close, fast=fast, slow=slow, signal=signal)
    macd_line = macd.iloc[:, 0]
    signal_line = macd.iloc[:, 2]
    entries = macd_line > signal_line
    exits = macd_line < signal_line

    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq="1D")
    stats = pf.stats()

    return {
        "strategy_name": "MACD Momentum",
        "total_return": f"{stats['Total Return [%]']:.2f}%",
        "sharpe_ratio": round(stats['Sharpe Ratio'], 2),
        "win_rate": f"{stats['Win Rate [%]']:.2f}%",
        "max_drawdown": f"{stats['Max Drawdown [%]']:.2f}%",
        "total_trades": stats['Total Trades'],
    }
