import pandas_ta as ta


def get_ebsw(df):
    """STRATEGY: Ehlers Cycle indicator. USE: Identifying exact turning points in cyclic markets."""
    return ta.ebsw(df["Close"]).tail(10).to_dict()
