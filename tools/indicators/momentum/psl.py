import pandas_ta as ta


def get_psl(df, length=12):
    res = ta.psl(df["Close"], length=length)
    return res.tail(10).to_dict()
