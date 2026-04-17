import pandas_ta as ta


def get_aroon(df, length=14):
    """
    STRATEGY: Identifies when a new trend is starting.
    WHEN TO USE: Spotting the transition from range to trend.
    MARKET CONDITION: Early breakout stages.
    """
    res = ta.aroon(df["High"], df["Low"], length=length)
    return res.tail(10).to_dict()
