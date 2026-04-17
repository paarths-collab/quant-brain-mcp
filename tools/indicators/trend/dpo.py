import pandas_ta as ta


def get_dpo(df, length=20):
    """
    STRATEGY: Removes trend to highlight short-term cycles.
    WHEN TO USE: Swing trading in a sideways market.
    MARKET CONDITION: Non-trending, cyclic markets.
    """
    res = ta.dpo(df["Close"], length=length)
    return res.tail(10).to_dict()
