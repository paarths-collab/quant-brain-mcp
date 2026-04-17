import pandas_ta as ta


def get_vwap(df):
    """
    STRATEGY: True intraday benchmark price based on volume.
    WHEN TO USE: Day trading ONLY (resets daily).
    SITUATION: Institutional buyers try to buy below VWAP. Trading above VWAP is bullish.
    """
    res = ta.vwap(df["High"], df["Low"], df["Close"], df["Volume"])
    return res.tail(10).to_dict()
