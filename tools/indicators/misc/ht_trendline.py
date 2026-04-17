import pandas_ta as ta


def get_ht_trendline(df):
    """STRATEGY: Instantaneous Trendline. USE: Distinguishing trend from cycle in choppy markets."""
    return ta.ht_trendline(df["Close"]).tail(10).to_dict()
