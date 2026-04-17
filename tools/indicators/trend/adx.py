import pandas_ta as ta


def get_adx(df, length=14):
    """
    STRATEGY: Measures trend strength (not direction). ADX > 25 = Strong trend.
    WHEN TO USE: To decide if a trend-following tool should be used.
    MARKET CONDITION: Distinguishes between trending and non-trending markets.
    """
    res = ta.adx(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
