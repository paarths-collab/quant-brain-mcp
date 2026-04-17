import pandas_ta as ta


def get_bbands(df, length=20, std=2):
    """
    STRATEGY: Mean reversion (buy at lower band, sell at upper) or "The Squeeze" (breakout).
    WHEN TO USE: Identifying overbought/oversold levels.
    MARKET CONDITION: Sideways/Ranging markets for reversion; Low-volatility markets for Squeeze plays.
    """
    res = ta.bbands(df["Close"], length=length, std=std)
    return res.tail(10).to_dict()
