import pandas_ta as ta


def get_ssf3(df, length=10):
    """
    STRATEGY: Sharper version of SSF.
    WHEN TO USE: Precise trend turning points.
    SITUATION: Use when SSF is too slow for fast market reversals.
    """
    res = ta.ssf3(df["Close"], length=length)
    return res.tail(10).to_dict()
