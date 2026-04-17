import pandas_ta as ta


def get_uo(df):
    res = ta.uo(df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
