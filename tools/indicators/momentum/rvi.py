import pandas_ta as ta


def get_rvi(df, length=14):
    res = ta.rvi(df["Close"], length=length)
    return res.tail(10).to_dict()
