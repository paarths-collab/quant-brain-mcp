import vectorbt as vbt

from tools.strategies._common import history_error, pct, positive_int, ratio
import pandas_ta as ta


def run_strategy(df, rsi_lower=30, rsi_upper=70):
    """
    STRATEGY: Buys when RSI is oversold and price is at the lower Bollinger Band.
    WHEN TO USE: When a stock has crashed too fast and is due for a bounce.
    MARKET CONDITION: Range-bound or temporarily overextended markets.
    RISK: Falling Knife if bad news persists.
    """
    if not 0 <= rsi_lower < rsi_upper <= 100:
        return {"error": "RSI thresholds must satisfy 0 <= rsi_lower < rsi_upper <= 100."}
    close = df["Close"]
    error = history_error(close, 21, "RSI-BB Mean Reversion")
    if error:
        return error
    rsi = ta.rsi(close, length=14)
    bbands = ta.bbands(close, length=20, std=2)

    entries = (rsi < rsi_lower) & (close < bbands.iloc[:, 0])
    exits = (rsi > rsi_upper) | (close > bbands.iloc[:, 2])

    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq="1D")
    stats = pf.stats()

    return {
        "strategy_name": "RSI-BB Mean Reversion",
        "win_rate": pct(stats['Win Rate [%]']),
        "max_drawdown": pct(stats['Max Drawdown [%]']),
        "expectancy": stats.get("Expectancy", None),
        "total_return": pct(stats['Total Return [%]']),
        "sharpe_ratio": ratio(stats['Sharpe Ratio']),
    }
