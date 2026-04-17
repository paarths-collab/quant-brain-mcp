import pandas_ta as ta


def get_massi(df):
    """
    STRATEGY: Identifies trend reversals by measuring the narrowing/widening of price range.
    WHEN TO USE: Predicting a "Reversal Bulge."
    MARKET CONDITION: Exhaustion phases at the end of a long trend.
    """
    res = ta.massi(df["High"], df["Low"])
    return res.tail(10).to_dict()
