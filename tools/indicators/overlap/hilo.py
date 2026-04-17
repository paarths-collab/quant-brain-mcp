import pandas_ta as ta


def get_hilo(df, high_length=13, low_length=13):
    """
    STRATEGY: Trend-following based on Highs/Lows.
    WHEN TO USE: Stop-loss placement.
    SITUATION: When the price is above HiLo, stay long. Below, stay short.
    """
    res = ta.hilo(df["High"], df["Low"], df["Close"], high_length=high_length, low_length=low_length)
    return res.tail(10).to_dict()
