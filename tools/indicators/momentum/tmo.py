import pandas_ta as ta


def get_tmo(df, length=14):
    res = ta.tmo(df["Close"], length=length)
    return res.tail(10).to_dict()
