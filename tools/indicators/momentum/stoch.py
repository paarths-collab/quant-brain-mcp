import pandas_ta as ta


def get_stoch(df, k=14, d=3):
    res = ta.stoch(df["High"], df["Low"], df["Close"], k=k, d=d)
    return res.tail(10).to_dict()
