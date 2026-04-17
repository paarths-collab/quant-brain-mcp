import pandas_ta as ta


def get_zlma(df, length=10):
    """
    STRATEGY: Offsets EMA to cancel out lag.
    WHEN TO USE: High-speed trend analysis.
    SITUATION: Perfect for 'Golden Cross' style strategies where you want the signal immediately.
    """
    res = ta.zlma(df["Close"], length=length)
    return res.tail(10).to_dict()
