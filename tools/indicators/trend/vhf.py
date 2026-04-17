import pandas_ta as ta


def get_vhf(df, length=28):
    """
    STRATEGY: Identifies whether price is in a trending or congestion phase.
    WHEN TO USE: Similar to ADX but more sensitive to vertical price moves.
    MARKET CONDITION: Consolidation vs. Expansion.
    """
    res = ta.vhf(df["Close"], length=length)
    return res.tail(10).to_dict()
