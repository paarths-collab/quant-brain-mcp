import pandas_ta as ta


def get_wcp(df):
    """
    STRATEGY: (High + Low + 2*Close) / 4.
    WHEN TO USE: Calculating a more accurate daily 'summary'.
    SITUATION: Gives double importance to the closing price.
    """
    res = ta.wcp(df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
