import pandas_ta as ta


def get_kurtosis(df):
    """STRATEGY: Probability of "Fat Tails" (Crashes). USE: Risk assessment for Indian volatility."""
    return ta.kurtosis(df["Close"]).tail(10).to_dict()
