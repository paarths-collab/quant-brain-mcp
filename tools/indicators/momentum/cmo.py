import pandas_ta as ta


def get_cmo(df, length=14):
    res = ta.cmo(df["Close"], length=length)
    return res.tail(10).to_dict()
