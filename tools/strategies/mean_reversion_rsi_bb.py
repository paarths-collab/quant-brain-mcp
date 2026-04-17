import vectorbt as vbt
import pandas_ta as ta


def run_strategy(df, rsi_lower=30, rsi_upper=70):
    """
    STRATEGY: Buys when RSI is oversold and price is at the lower Bollinger Band.
    WHEN TO USE: When a stock has crashed too fast and is due for a bounce.
    MARKET CONDITION: Range-bound or temporarily overextended markets.
    RISK: Falling Knife if bad news persists.
    """
    close = df["Close"]
    rsi = ta.rsi(close, length=14)
    bbands = ta.bbands(close, length=20, std=2)

    entries = (rsi < rsi_lower) & (close < bbands.iloc[:, 0])
    exits = (rsi > rsi_upper) | (close > bbands.iloc[:, 2])

    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001)
    stats = pf.stats()

    return {
        "strategy_name": "RSI-BB Mean Reversion",
        "win_rate": f"{stats['Win Rate [%]']:.2f}%",
        "max_drawdown": f"{stats['Max Drawdown [%]']:.2f}%",
        "expectancy": stats.get("Expectancy", None),
        "total_return": f"{stats['Total Return [%]']:.2f}%",
        "sharpe_ratio": round(stats['Sharpe Ratio'], 2),
    }
