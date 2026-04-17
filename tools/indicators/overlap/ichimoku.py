import pandas_ta as ta


def get_ichimoku(df):
    """
    STRATEGY: All-in-one trend, support, and momentum.
    WHEN TO USE: Full market analysis.
    SITUATION: Price above the 'Cloud' is bullish. Cloud thickness indicates strength of support.
    """
    res, _ = ta.ichimoku(df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
