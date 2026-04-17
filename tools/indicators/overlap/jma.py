import pandas_ta as ta


def get_jma(df, length=7, phase=0):
    """
    STRATEGY: Advanced smoothing with minimal overshoot.
    WHEN TO USE: Professional quant trading.
    SITUATION: Use to avoid 'whipsaws' in sideways markets.
    """
    res = ta.jma(df["Close"], length=length, phase=phase)
    return res.tail(10).to_dict()
