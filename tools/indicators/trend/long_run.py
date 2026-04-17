import pandas_ta as ta


def get_long_run(df):
    """
    STRATEGY: Identifies long-term trend persistence.
    WHEN TO USE: Long-term investors (Portfolio building).
    MARKET CONDITION: Multi-year bull/bear cycles.
    """
    res = ta.long_run(df["Close"])
    return res.tail(10).to_dict()
