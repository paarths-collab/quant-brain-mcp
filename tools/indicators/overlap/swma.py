import pandas_ta as ta


def get_swma(df, length=10):
    """
    STRATEGY: Symmetrical weighting of price data.
    WHEN TO USE: Identifying the 'center of mass' of price action.
    SITUATION: Good for finding the 'fair value' over a period.
    """
    res = ta.swma(df["Close"], length=length)
    return res.tail(10).to_dict()
