import pandas_ta as ta


def get_psar(df):
    """
    STRATEGY: Trailing stop that "accelerates" toward the price.
    WHEN TO USE: Determining when to flip a position from Long to Short.
    MARKET CONDITION: Strong, clear trending markets. Terrible in sideways markets.
    """
    res = ta.psar(df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
