import pandas_ta as ta


def get_eom(df, length=14):
    """
    STRATEGY: Relates price change to volume. High values = Price moving up on low effort.
    WHEN TO USE: Spotting thin markets or low-resistance paths.
    MARKET CONDITION: Trending markets with varying liquidity.
    """
    res = ta.eom(df["High"], df["Low"], df["Close"], df["Volume"], length=length)
    return res.tail(10).to_dict()
