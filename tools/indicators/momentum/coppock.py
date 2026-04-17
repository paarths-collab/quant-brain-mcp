import pandas_ta as ta


def get_coppock(df):
    res = ta.coppock(df["Close"])
    return res.tail(10).to_dict()
