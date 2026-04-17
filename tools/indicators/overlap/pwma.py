import pandas_ta as ta


def get_pwma(df, length=10):
    """
    STRATEGY: Uses Pascal's triangle coefficients for weighting.
    WHEN TO USE: Bell-curve style price weighting.
    SITUATION: Heavily emphasizes the middle of the lookback period.
    """
    res = ta.pwma(df["Close"], length=length)
    return res.tail(10).to_dict()
