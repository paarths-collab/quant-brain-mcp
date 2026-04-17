import pandas_ta as ta


def get_sma(df, length=50):
    """
    STRATEGY: Equal weighting for all days.
    WHEN TO USE: Institutional level analysis.
    SITUATION: 50 SMA and 200 SMA are the primary 'gravity' lines for all big funds.
    """
    res = ta.sma(df["Close"], length=length)
    return res.tail(10).to_dict()
