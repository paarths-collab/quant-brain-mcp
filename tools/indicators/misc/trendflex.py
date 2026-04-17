import pandas_ta as ta


def get_trendflex(df):
    """STRATEGY: High-performance trend measure. USE: Filtering noise in short-term trades."""
    return ta.trendflex(df["Close"]).tail(10).to_dict()
