import pandas_ta as ta


def get_mfi(df, length=14):
    """
    STRATEGY: A volume-weighted RSI.
    WHEN TO USE: Spotting overbought (>80) or oversold (<20) levels.
    MARKET CONDITION: Ranging markets or parabolic moves.
    """
    res = ta.mfi(df["High"], df["Low"], df["Close"], df["Volume"], length=length)
    return res.tail(10).to_dict()
