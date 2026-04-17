import pandas_ta as ta


def get_apo(df, fast=12, slow=26):
    res = ta.apo(df["Close"], fast=fast, slow=slow)
    return res.tail(10).to_dict()
