import pandas_ta as ta


def get_log_return(df):
    """STRATEGY: Logarithmic returns. USE: For normal distribution modeling of returns."""
    return ta.log_return(df["Close"]).tail(10).to_dict()
