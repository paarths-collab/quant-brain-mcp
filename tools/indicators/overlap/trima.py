import pandas_ta as ta


def get_trima(df, length=10):
    """
    STRATEGY: Double-smoothed SMA.
    WHEN TO USE: General market overview.
    SITUATION: Produces a wave-like line that is very steady against price spikes.
    """
    res = ta.trima(df["Close"], length=length)
    return res.tail(10).to_dict()
