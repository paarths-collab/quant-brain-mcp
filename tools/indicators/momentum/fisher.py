import pandas_ta as ta


def get_fisher(df, length=9):
    res = ta.fisher(df["High"], df["Low"], length=length)
    return res.tail(10).to_dict()
