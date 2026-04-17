import pandas_ta as ta


def get_cmf(df, length=20):
    """
    STRATEGY: Measures the amount of Money Flow Volume over a specific period.
    WHEN TO USE: Buy signals when CMF crosses above 0.
    MARKET CONDITION: Trending markets. Confirms if "Smart Money" is participating in the move.
    """
    res = ta.cmf(df["High"], df["Low"], df["Close"], df["Volume"], length=length)
    return res.tail(10).to_dict()
