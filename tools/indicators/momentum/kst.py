import pandas_ta as ta


def get_kst(df):
    res = ta.kst(df["Close"])
    return res.tail(10).to_dict()
