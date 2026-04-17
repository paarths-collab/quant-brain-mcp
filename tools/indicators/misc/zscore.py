import pandas_ta as ta


def get_zscore(df):
    """STRATEGY: Distance from the mean in StDev units. USE: Buy when Z < -2 (extreme oversold)."""
    return ta.zscore(df["Close"]).tail(10).to_dict()
