import pandas_ta as ta


def get_pvt(df):
    """
    STRATEGY: Similar to OBV but uses percentage price change.
    WHEN TO USE: More sensitive trend confirmation.
    MARKET CONDITION: Steady, low-volatility trending markets.
    """
    res = ta.pvt(df["Close"], df["Volume"])
    return res.tail(10).to_dict()
