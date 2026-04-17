import pandas_ta as ta


def get_pvi(df):
    """
    STRATEGY: Focuses on days where volume increases (Crowd Money days).
    WHEN TO USE: Identifying market tops (when the "uninformed" crowd rushes in).
    MARKET CONDITION: Late-stage rallies or "Hype" cycles.
    """
    res = ta.pvi(df["Close"], df["Volume"])
    return res.tail(10).to_dict()
