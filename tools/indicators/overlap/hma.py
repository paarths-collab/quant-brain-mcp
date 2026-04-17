import pandas_ta as ta


def get_hma(df, length=16):
    """
    STRATEGY: Extremely fast, zero-lag MA.
    WHEN TO USE: When you want to eliminate lag entirely.
    SITUATION: Identifying the 'immediate' trend direction in fast-moving stocks like NVDA or RELIANCE.
    """
    res = ta.hma(df["Close"], length=length)
    return res.tail(10).to_dict()
