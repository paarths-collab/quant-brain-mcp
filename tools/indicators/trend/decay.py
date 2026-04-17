import pandas_ta as ta


def get_decay(df, length=5):
    """
    STRATEGY: Linear or exponential decay of a signal.
    WHEN TO USE: Weighting recent signals more heavily than old ones.
    MARKET CONDITION: Rapidly changing price action.
    """
    res = ta.decay(df["Close"], length=length)
    return res.tail(10).to_dict()
