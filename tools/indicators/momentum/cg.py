import pandas_ta as ta


def get_cg(df, length=10):
    res = ta.cg(df["Close"], length=length)
    return res.tail(10).to_dict()
