import pandas_ta as ta


def get_ad(df):
    """
    STRATEGY: Measures the cumulative flow of money into or out of a stock.
    WHEN TO USE: To confirm a trend. If price is rising but A/D is falling, the trend is weak.
    MARKET CONDITION: Trending markets. Best for spotting "Hidden Distribution" by institutions.
    """
    res = ta.ad(df["High"], df["Low"], df["Close"], df["Volume"])
    return res.tail(10).to_dict()
