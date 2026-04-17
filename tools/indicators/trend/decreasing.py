import pandas_ta as ta


def get_decreasing(df, length=2):
    """
    STRATEGY: Returns 1 if values are strictly decreasing.
    WHEN TO USE: Detecting a falling knife or persistent sell-off.
    MARKET CONDITION: Strong Bearish sentiment.
    """
    res = ta.decreasing(df["Close"], length=length)
    return res.tail(10).to_dict()
