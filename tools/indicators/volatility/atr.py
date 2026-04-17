import pandas_ta as ta


def get_atr(df, length=14):
    """
    STRATEGY: Measures the absolute volatility of a stock.
    WHEN TO USE: Setting Stop-Losses. A common strategy is 2x ATR from entry.
    MARKET CONDITION: All conditions. High ATR = High risk/High reward; Low ATR = Consolidation.
    """
    res = ta.atr(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
