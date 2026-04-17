import pandas_ta as ta


def get_stdev(df, length=30):
    """
    STRATEGY: Core measure of volatility.
    WHEN TO USE: Assessing investment risk.
    MARKET CONDITION: All. High StDev suggests high emotional market activity.
    """
    res = ta.stdev(df["Close"], length=length)
    return res.tail(10).to_dict()
