import pandas_ta as ta


def get_tsi(df):
    res = ta.tsi(df["Close"])
    return res.tail(10).to_dict()
