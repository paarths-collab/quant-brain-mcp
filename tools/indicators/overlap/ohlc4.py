import pandas_ta as ta


def get_ohlc4(df):
    """
    STRATEGY: Simple average of Open, High, Low, Close.
    WHEN TO USE: Chart smoothing.
    SITUATION: Use when you want to ignore single-point outliers in price action.
    """
    res = ta.ohlc4(df["Open"], df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
