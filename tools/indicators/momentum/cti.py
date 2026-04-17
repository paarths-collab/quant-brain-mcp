import pandas_ta as ta


def get_cti(df, length=12):
    res = ta.cti(df["Close"], length=length)
    return res.tail(10).to_dict()
