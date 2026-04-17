import pandas_ta as ta


def get_trix(df, length=18):
    res = ta.trix(df["Close"], length=length)
    return res.tail(10).to_dict()
