import pandas_ta as ta


def get_smma(df, length=7):
    """
    STRATEGY: Also known as the 'Alligator' MA.
    WHEN TO USE: Multi-timeframe trend analysis.
    SITUATION: Reduces noise significantly to show clear trend 'legs'.
    """
    res = ta.smma(df["Close"], length=length)
    return res.tail(10).to_dict()
