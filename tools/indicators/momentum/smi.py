import pandas_ta as ta


def get_smi(df, length=13, signal=25):
    res = ta.smi(df["Close"], length=length, signal=signal)
    return res.tail(10).to_dict()
