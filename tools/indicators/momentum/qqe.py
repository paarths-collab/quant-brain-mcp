import pandas_ta as ta


def get_qqe(df, length=14):
    res = ta.qqe(df["Close"], length=length)
    return res.tail(10).to_dict()
