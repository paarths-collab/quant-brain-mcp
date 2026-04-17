import pandas_ta as ta


def get_xsignals(df):
    """
    STRATEGY: Cross-signal detection tool.
    WHEN TO USE: Finding technical intersections.
    MARKET CONDITION: Complex environments with multiple indicators.
    """
    res = ta.xsignals(df["Close"])
    return res.tail(10).to_dict()
