import pandas_ta as ta


def get_vortex(df, length=14):
    """
    STRATEGY: Two lines (VI+ and VI-) that identify trend start and strength.
    WHEN TO USE: Identifying trend crossovers. Bullish if VI+ crosses VI-.
    MARKET CONDITION: High-momentum trending markets.
    """
    res = ta.vortex(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
