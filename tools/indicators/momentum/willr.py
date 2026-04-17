import pandas_ta as ta


def get_willr(df, length=14):
    res = ta.willr(df["High"], df["Low"], df["Close"], length=length)
    return res.tail(10).to_dict()
