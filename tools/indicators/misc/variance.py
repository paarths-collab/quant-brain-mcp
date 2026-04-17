import pandas_ta as ta


def get_variance(df):
    """STRATEGY: Mathematical volatility. USE: Input for portfolio math."""
    return ta.variance(df["Close"]).tail(10).to_dict()
