import pandas_ta as ta


def get_cfo(df, length=9):
    res = ta.cfo(df["Close"], length=length)
    return res.tail(10).to_dict()
