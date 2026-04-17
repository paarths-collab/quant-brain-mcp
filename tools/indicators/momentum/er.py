import pandas_ta as ta


def get_er(df, length=10):
    res = ta.er(df["Close"], length=length)
    return res.tail(10).to_dict()
