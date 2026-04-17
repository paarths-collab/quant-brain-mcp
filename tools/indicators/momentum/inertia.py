import pandas_ta as ta


def get_inertia(df, length=20):
    res = ta.inertia(df["Close"], length=length)
    return res.tail(10).to_dict()
