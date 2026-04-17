import pandas_ta as ta


def get_entropy(df):
    """STRATEGY: Measures market complexity/chaos. USE: High entropy = Avoid trading (unpredictable)."""
    return ta.entropy(df["Close"]).tail(10).to_dict()
