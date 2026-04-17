import pandas_ta as ta


def get_macd(df, fast=12, slow=26, signal=9):
    res = ta.macd(df["Close"], fast=fast, slow=slow, signal=signal)
    return res.tail(10).to_dict()
