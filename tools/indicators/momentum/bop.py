import pandas_ta as ta


def get_bop(df):
    res = ta.bop(df["Open"], df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
