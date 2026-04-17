import pandas_ta as ta


def get_qstick(df, length=10):
    """
    STRATEGY: Moving average of (Close - Open).
    WHEN TO USE: Identifying candlestick strength over a period.
    MARKET CONDITION: Assessing intra-day buying/selling pressure.
    """
    res = ta.qstick(df["Open"], df["Close"], length=length)
    return res.tail(10).to_dict()
