import pandas_ta as ta


def get_skew(df):
    """STRATEGY: Asymmetry of returns. USE: Spotting if a stock is prone to "gap ups" or "gap downs"."""
    return ta.skew(df["Close"]).tail(10).to_dict()
