import pandas_ta as ta


def get_tema(df, length=10):
    """
    STRATEGY: Triple smoothing to drastically reduce lag.
    WHEN TO USE: Aggressive day trading.
    SITUATION: Best for catching sudden momentum shifts in low-liquidity stocks.
    """
    res = ta.tema(df["Close"], length=length)
    return res.tail(10).to_dict()
