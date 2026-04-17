import pandas_ta as ta


def get_alma(df, length=9, sigma=6, distribution=0.85):
    """
    STRATEGY: Reduces lag while maintaining smoothness.
    WHEN TO USE: In trending markets where standard EMAs are too slow.
    SITUATION: Use to identify trend changes earlier without being caught by 'noise'.
    """
    res = ta.alma(df["Close"], length=length, sigma=sigma, distribution=distribution)
    return res.tail(10).to_dict()
