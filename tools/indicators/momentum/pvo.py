import pandas_ta as ta


def get_pvo(df, fast=12, slow=26):
    res = ta.pvo(df["Volume"], fast=fast, slow=slow)
    return res.tail(10).to_dict()
