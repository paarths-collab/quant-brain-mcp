import pandas_ta as ta


def get_kvo(df, fast=34, slow=55):
    """
    STRATEGY: Compares volume to price and summarizes it into an oscillator.
    WHEN TO USE: Long-term money flow reversals.
    MARKET CONDITION: Mature trends. Divergence here is a very strong exit signal.
    """
    res = ta.kvo(df["High"], df["Low"], df["Close"], df["Volume"], fast=fast, slow=slow)
    return res.tail(10).to_dict()
