import pandas_ta as ta


def get_chop(df, length=14):
    """
    STRATEGY: Measures how "choppy" the market is. Higher = More choppy.
    WHEN TO USE: To avoid being "whipsawed" in sideways markets.
    MARKET CONDITION: Non-trending/Sideways.
    """
    res = ta.chop(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
