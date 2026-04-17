import pandas_ta as ta


def get_hwc(df):
    """
    STRATEGY: Forecasts price channel based on triple exponential smoothing.
    WHEN TO USE: Volatility analysis.
    SITUATION: Predicting price boundaries in stocks with strong seasonality/cycles.
    """
    res = ta.hwc(df["Close"])
    return res.tail(10).to_dict()
