import pandas_ta as ta


def get_aroon(df, length=14):
    res = ta.aroon(df["High"], df["Low"], length=length)
    return res.tail(10).to_dict()
