import pandas_ta as ta


def get_dm(df, length=14):
    """
    STRATEGY: Core component of ADX; tracks +DM and -DM.
    WHEN TO USE: Identifying trend direction (Bullish if +DM > -DM).
    MARKET CONDITION: All trending environments.
    """
    res = ta.dm(df["High"], df["Low"], length=length)
    return res.tail(10).to_dict()
