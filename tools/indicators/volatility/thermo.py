import pandas_ta as ta


def get_thermo(df):
    """
    STRATEGY: Distinguishes between trending and cyclical (ranging) market modes.
    WHEN TO USE: To stop trading trend-strategies in flat markets.
    MARKET CONDITION: Transitional markets moving from trend to range.
    """
    res = ta.thermo(df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
