import pandas_ta as ta


def get_stochrsi(df, length=14):
    res = ta.stochrsi(df["Close"], length=length)
    return res.tail(10).to_dict()
