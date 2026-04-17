import pandas_ta as ta


def get_midpoint(df, length=14):
    """
    STRATEGY: Average of Highest High and Lowest Low.
    WHEN TO USE: Equilibrium analysis.
    SITUATION: Shows the 50% retracement level for a given lookback period.
    """
    res = ta.midpoint(df["Close"], length=length)
    return res.tail(10).to_dict()
