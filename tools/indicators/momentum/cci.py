import pandas_ta as ta


def get_cci(df, length=14):
    res = ta.cci(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
