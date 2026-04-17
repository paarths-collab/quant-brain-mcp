import pandas_ta as ta


def get_percent_return(df):
    """STRATEGY: Simple ROI. USE: Reporting performance to the user."""
    return ta.percent_return(df["Close"]).tail(10).to_dict()
