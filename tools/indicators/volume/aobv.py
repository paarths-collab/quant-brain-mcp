import pandas_ta as ta


def get_aobv(df):
    """
    STRATEGY: Enhanced OBV that uses moving averages to smooth volume flow.
    WHEN TO USE: Confirmation of breakout strength.
    MARKET CONDITION: High-volume breakouts in US Tech or Indian Blue-chips.
    """
    res = ta.aobv(df["Close"], df["Volume"])
    return res.tail(10).to_dict()
