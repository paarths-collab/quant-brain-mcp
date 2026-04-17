import pandas_ta as ta


def get_mad(df):
    """STRATEGY: Stable volatility measure. USE: When StDev is too influenced by outliers."""
    return ta.mad(df["Close"]).tail(10).to_dict()
