import pandas_ta as ta


def get_stc(df):
    res = ta.stc(df["Close"])
    return res.tail(10).to_dict()
