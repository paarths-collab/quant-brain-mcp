import pandas_ta as ta


def get_cksp(df):
    """
    STRATEGY: Volatility-based stop-loss for trend following.
    WHEN TO USE: Exit management for winning trades.
    MARKET CONDITION: High-volatility trending markets.
    """
    res = ta.cksp(df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
