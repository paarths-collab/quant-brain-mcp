import pandas_ta as ta


def get_fwma(df, length=10):
    """
    STRATEGY: Uses Fibonacci sequence for weighting.
    WHEN TO USE: Markets respecting Fibonacci levels.
    SITUATION: Identify cycle turning points based on mathematical growth patterns.
    """
    res = ta.fwma(df["Close"], length=length)
    return res.tail(10).to_dict()
