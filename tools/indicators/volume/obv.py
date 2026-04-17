import pandas_ta as ta


def get_obv(df):
    """
    STRATEGY: Running total of volume based on whether price closed up or down.
    WHEN TO USE: Predicting price breakouts. Volume usually precedes price.
    MARKET CONDITION: All. A staple for checking if a rally has "legs."
    """
    res = ta.obv(df["Close"], df["Volume"])
    return res.tail(10).to_dict()
