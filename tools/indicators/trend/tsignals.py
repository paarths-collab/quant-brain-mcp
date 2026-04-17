import pandas_ta as ta


def get_tsignals(df):
    """
    STRATEGY: Generates buy/sell signals based on trend changes.
    WHEN TO USE: Systematic trading strategy foundation.
    MARKET CONDITION: Trending markets.
    """
    res = ta.tsignals(df["Close"])
    return res.tail(10).to_dict()
