import pandas_ta as ta


def get_kc(df, length=20, scalar=2):
    """
    STRATEGY: Similar to Bollinger Bands but uses ATR instead of Standard Deviation.
    WHEN TO USE: Filtering out price noise.
    MARKET CONDITION: Trending markets. It is more robust than BBands for trend-following.
    """
    res = ta.kc(df["High"], df["Low"], df["Close"], length=length, scalar=scalar)
    return res.tail(10).to_dict()
