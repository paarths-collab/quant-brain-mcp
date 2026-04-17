import pandas_ta as ta


def get_quantile(df, q=0.5):
    """STRATEGY: Statistical price floors/ceilings. USE: Identifying support zones."""
    return ta.quantile(df["Close"], q=q).tail(10).to_dict()
