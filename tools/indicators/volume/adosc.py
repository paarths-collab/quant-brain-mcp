import pandas_ta as ta


def get_adosc(df, fast=3, slow=10):
    """
    STRATEGY: Momentum of the Accumulation/Distribution Line.
    WHEN TO USE: Identifying broad market turning points.
    MARKET CONDITION: Accumulation phases. Use when a stock is sideways to see which way it will break.
    """
    res = ta.adosc(df["High"], df["Low"], df["Close"], df["Volume"], fast=fast, slow=slow)
    return res.tail(10).to_dict()
