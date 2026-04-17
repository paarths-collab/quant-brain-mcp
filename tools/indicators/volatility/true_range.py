import pandas_ta as ta


def get_true_range(df):
    """
    STRATEGY: Base calculation for ATR.
    WHEN TO USE: Custom volatility formulas.
    MARKET CONDITION: Intraday high-volatility analysis.
    """
    res = ta.true_range(df["High"], df["Low"], df["Close"])
    return res.tail(10).to_dict()
