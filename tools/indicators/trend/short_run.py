import pandas_ta as ta


def get_short_run(df):
    """
    STRATEGY: Identifies short-term price momentum.
    WHEN TO USE: Day trading or Scalping.
    MARKET CONDITION: Intraday spikes or dips.
    """
    res = ta.short_run(df["Close"])
    return res.tail(10).to_dict()
