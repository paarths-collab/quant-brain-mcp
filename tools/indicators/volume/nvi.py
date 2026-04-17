import pandas_ta as ta


def get_nvi(df):
    """
    STRATEGY: Focuses on days where volume decreases (Smart Money days).
    WHEN TO USE: Long-term "Buy and Hold" confirmation.
    MARKET CONDITION: Bull markets. If NVI is above its 255-day EMA, it's a long-term bull.
    """
    res = ta.nvi(df["Close"], df["Volume"])
    return res.tail(10).to_dict()
