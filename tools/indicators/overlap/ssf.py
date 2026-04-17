import pandas_ta as ta


def get_ssf(df, length=10):
    """
    STRATEGY: Ehlers filter to remove aliasing noise.
    WHEN TO USE: High frequency or 'noisy' data.
    SITUATION: When you need the cleanest possible line to identify trend direction.
    """
    res = ta.ssf(df["Close"], length=length)
    return res.tail(10).to_dict()
