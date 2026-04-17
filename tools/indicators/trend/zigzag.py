import pandas_ta as ta


def get_zigzag(df):
    """
    STRATEGY: Filters out small price changes to show major swings.
    WHEN TO USE: Elliot Wave analysis or identifying major support/resistance.
    MARKET CONDITION: All. Useful for long-term historical structural analysis.
    """
    res = ta.zigzag(df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
