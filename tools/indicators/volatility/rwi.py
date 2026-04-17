import pandas_ta as ta


def get_rwi(df, length=14):
    """
    STRATEGY: Determines if price movement is "Random" or part of a statistically significant trend.
    WHEN TO USE: Deciding between Trend-Following or Swing-Trading.
    MARKET CONDITION: Ambiguous markets where trend strength is unclear.
    """
    res = ta.rwi(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
