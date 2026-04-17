import pandas_ta as ta


def get_kdj(df, length=9, signal=3):
    res = ta.kdj(df["High"], df["Low"], df["Close"], length=length, signal=signal)
    return res.tail(10).to_dict()
