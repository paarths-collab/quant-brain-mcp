import pandas_ta as ta


def get_slope(df, length=1):
    res = ta.slope(df["Close"], length=length)
    return res.tail(10).to_dict()
