import pandas_ta as ta


def get_aberration(df, length=15):
    """
    STRATEGY: Uses a channel based on SMA and Mean Absolute Deviation.
    WHEN TO USE: Identifying price extremes.
    MARKET CONDITION: Trending markets. It helps identify when a trend is overextending.
    """
    res = ta.aberration(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
