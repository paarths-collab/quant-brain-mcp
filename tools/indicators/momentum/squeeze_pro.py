import pandas_ta as ta


def get_squeeze_pro(df):
    res = ta.squeeze_pro(df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
