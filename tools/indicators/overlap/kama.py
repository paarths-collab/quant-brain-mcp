import pandas_ta as ta


def get_kama(df, length=10):
    """
    STRATEGY: Speeds up in trends, slows down in range.
    WHEN TO USE: All-weather trend indicator.
    SITUATION: Best for stocks that alternate between high volatility and consolidation.
    """
    res = ta.kama(df["Close"], length=length)
    return res.tail(10).to_dict()
