import pandas_ta as ta


def get_sinwma(df, length=14):
    """
    STRATEGY: Weights price based on a Sine wave.
    WHEN TO USE: Markets with clear cyclicality.
    SITUATION: Better at catching 'waves' than a simple linear MA.
    """
    res = ta.sinwma(df["Close"], length=length)
    return res.tail(10).to_dict()
