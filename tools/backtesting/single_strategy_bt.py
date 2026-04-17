import vectorbt as vbt
import pandas_ta as ta


def run_single_backtest(df, indicator_type="rsi", upper=70, lower=30):
    """
    STRATEGY: Buy when indicator is low, sell when high.
    WHEN TO USE: Mean reversion strategies.
    VERDICT: Tells the Agent if a stock is 'oversold' enough to bounce.
    """
    close = df["Close"]
    if indicator_type == "rsi":
        ind = ta.rsi(close)
        entries = ind < lower
        exits = ind > upper

    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001)
    return pf.stats().to_dict()
