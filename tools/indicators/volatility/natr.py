import pandas_ta as ta


def get_natr(df, length=14):
    """
    STRATEGY: ATR expressed as a percentage.
    WHEN TO USE: Comparing volatility between different stocks (e.g., AAPL vs RELIANCE.NS).
    MARKET CONDITION: Multi-asset portfolio analysis.
    """
    res = ta.natr(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
