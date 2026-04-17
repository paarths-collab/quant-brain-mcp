import pandas_ta as ta


def get_wma(df, length=10):
    """
    STRATEGY: Linearly weighted MA.
    WHEN TO USE: General trend following.
    SITUATION: More sensitive than SMA but less aggressive than EMA.
    """
    res = ta.wma(df["Close"], length=length)
    return res.tail(10).to_dict()
