import pandas_ta as ta


def get_accbands(df, length=20):
    """
    STRATEGY: Volatility bands that expand/contract based on price acceleration.
    WHEN TO USE: Breakout trading.
    MARKET CONDITION: Fast-moving, trending markets. Use to stay in a trend as it accelerates.
    """
    res = ta.accbands(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
