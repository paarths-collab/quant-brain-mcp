import pandas_ta as ta


def get_hwma(df):
    """
    STRATEGY: Adaptive MA using trend and seasonality components.
    WHEN TO USE: Long-term structural trends.
    SITUATION: Filtering out seasonal noise in commodity stocks or retailers.
    """
    res = ta.hwma(df["Close"])
    return res.tail(10).to_dict()
