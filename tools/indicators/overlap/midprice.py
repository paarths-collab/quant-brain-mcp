import pandas_ta as ta


def get_midprice(df, length=14):
    """
    STRATEGY: Similar to Midpoint but uses High/Low instead of Close.
    WHEN TO USE: Determining the true price range center.
    SITUATION: Use to identify if price is trading in the upper or lower half of its recent range.
    """
    res = ta.midprice(df["High"], df["Low"], length=length)
    return res.tail(10).to_dict()
