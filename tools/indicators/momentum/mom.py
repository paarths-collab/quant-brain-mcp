import pandas_ta as ta


def get_mom(df, length=10):
    res = ta.mom(df["Close"], length=length)
    return res.tail(10).to_dict()
