import pandas_ta as ta


def get_ppo(df, fast=12, slow=26):
    res = ta.ppo(df["Close"], fast=fast, slow=slow)
    return res.tail(10).to_dict()
