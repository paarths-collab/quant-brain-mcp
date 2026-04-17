import pandas_ta as ta


def get_rvgi(df, length=14):
    res = ta.rvgi(df["Open"], df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
