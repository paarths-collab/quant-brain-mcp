import pandas_ta as ta


def get_squeeze(df):
    res = ta.squeeze(df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
