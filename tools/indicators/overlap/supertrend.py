import pandas_ta as ta


def get_supertrend(df, length=7, multiplier=3):
    """
    STRATEGY: Trend following based on ATR volatility.
    WHEN TO USE: Buy/Sell signal generation.
    SITUATION: Go Long when Green (price above), Short when Red (price below). Best for trending markets.
    """
    res = ta.supertrend(df["High"], df["Low"], df["Close"], length=length, multiplier=multiplier)
    return res.tail(10).to_dict()
