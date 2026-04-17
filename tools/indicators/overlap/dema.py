import pandas_ta as ta


def get_dema(df, length=10):
    """
    STRATEGY: Double smoothing to remove lag.
    WHEN TO USE: Scalping or fast-day trading.
    SITUATION: Use for quick trend confirmation in highly volatile Indian or US mid-caps.
    """
    res = ta.dema(df["Close"], length=length)
    return res.tail(10).to_dict()
