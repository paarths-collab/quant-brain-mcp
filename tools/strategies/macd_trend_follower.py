import vectorbt as vbt

from tools.strategies._common import history_error, pct, positive_int, ratio
import pandas_ta as ta


def run_backtest(df, fast=12, slow=26, signal=9):
    """Vectorized backtest for MACD trend following."""
    fast, slow, signal = (positive_int(n, v) for n, v in (("fast", fast), ("slow", slow), ("signal", signal)))
    if fast >= slow:
        return {"error": f"fast ({fast}) must be shorter than slow ({slow})."}
    close = df["Close"].astype(float)
    error = history_error(close, slow + signal, "MACD Trend Follower")
    if error:
        return error
    macd = ta.macd(close, fast=fast, slow=slow, signal=signal)
    macd_line = macd.iloc[:, 0]
    signal_line = macd.iloc[:, 2]
    entries = macd_line > signal_line
    exits = macd_line < signal_line

    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq="1D")
    stats = pf.stats()

    return {
        "strategy_name": "MACD Trend Follower",
        "total_return": pct(stats['Total Return [%]']),
        "sharpe_ratio": ratio(stats['Sharpe Ratio']),
        "win_rate": pct(stats['Win Rate [%]']),
        "max_drawdown": pct(stats['Max Drawdown [%]']),
        "total_trades": stats['Total Trades'],
    }
