import pandas_ta as ta


def get_amat(df):
    """
    STRATEGY: Trend signal based on two moving averages and ADX.
    WHEN TO USE: Systematic entry/exit.
    MARKET CONDITION: Established long-term trends.
    """
    res = ta.amat(df["Close"])
    return res.tail(10).to_dict()
