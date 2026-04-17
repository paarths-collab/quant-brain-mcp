import pandas_ta as ta


def get_eri(df, length=13):
    res = ta.eri(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
