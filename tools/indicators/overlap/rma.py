import pandas_ta as ta


def get_rma(df, length=10):
    """
    STRATEGY: Used internally by RSI for smoothing.
    WHEN TO USE: Replicating RSI-style smoothing on price.
    SITUATION: Very slow and stable; used for long-term trend baseline.
    """
    res = ta.rma(df["Close"], length=length)
    return res.tail(10).to_dict()
