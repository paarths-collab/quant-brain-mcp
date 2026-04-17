import pandas_ta as ta


def get_ema(df, length=20):
    """
    STRATEGY: Gives more weight to recent prices.
    WHEN TO USE: Trend following.
    SITUATION: EMA 20 is the 'mean' for short-term trends; EMA 200 is the long-term 'floor'.
    """
    res = ta.ema(df["Close"], length=length)
    return res.tail(10).to_dict()
