import pandas_ta as ta


def get_median(df):
    """STRATEGY: Rolling 50% percentile. USE: Baseline price for mean reversion."""
    return ta.median(df["Close"]).tail(10).to_dict()
