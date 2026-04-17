import pandas_ta as ta


def get_donchian(df, length=20):
    """
    STRATEGY: Tracks the highest high and lowest low of the last N periods.
    WHEN TO USE: Trend following (Turtle Trading strategy).
    MARKET CONDITION: Trending markets. Buy when price breaks the upper channel.
    """
    res = ta.donchian(df["High"], df["Low"], length=length)
    return res.tail(10).to_dict()
