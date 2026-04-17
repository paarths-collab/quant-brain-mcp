import pandas_ta as ta


def get_rsx(df, length=14):
    res = ta.rsx(df["Close"], length=length)
    return res.tail(10).to_dict()
