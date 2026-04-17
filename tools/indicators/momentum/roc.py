import pandas_ta as ta


def get_roc(df, length=10):
    res = ta.roc(df["Close"], length=length)
    return res.tail(10).to_dict()
