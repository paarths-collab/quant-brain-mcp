import pandas_ta as ta


def get_t3(df, length=5):
    """
    STRATEGY: Triple-smoothed MA with volume factor.
    WHEN TO USE: Modern trend following.
    SITUATION: Provides a much smoother line than EMA with less lag than SMA.
    """
    res = ta.t3(df["Close"], length=length)
    return res.tail(10).to_dict()
