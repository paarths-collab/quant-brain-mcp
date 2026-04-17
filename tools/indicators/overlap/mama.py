import pandas_ta as ta


def get_mama(df):
    """
    STRATEGY: Separates price into Phase and Amplitude.
    WHEN TO USE: To find cyclic turning points.
    SITUATION: Crosses of MAMA and FAMA (Following Adaptive MA) are highly reliable trend signals.
    """
    res = ta.mama(df["Close"])
    return res.tail(10).to_dict()
