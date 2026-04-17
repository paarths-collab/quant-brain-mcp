import pandas_ta as ta


def get_vwma(df, length=20):
    """
    STRATEGY: MA that gives more weight to high-volume days.
    WHEN TO USE: Confirming trend strength.
    SITUATION: If VWMA is rising and price is above it, the trend is supported by real money.
    """
    res = ta.vwma(df["Close"], df["Volume"], length=length)
    return res.tail(10).to_dict()
