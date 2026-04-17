import pandas_ta as ta


def get_increasing(df, length=2):
    """
    STRATEGY: Returns 1 if values are strictly increasing.
    WHEN TO USE: Spotting consistent momentum build-up.
    MARKET CONDITION: Strong Bullish sentiment.
    """
    res = ta.increasing(df["Close"], length=length)
    return res.tail(10).to_dict()
