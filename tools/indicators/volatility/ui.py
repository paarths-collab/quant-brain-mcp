import pandas_ta as ta


def get_ui(df, length=14):
    """
    STRATEGY: Measures downside risk/stress.
    WHEN TO USE: Portfolio risk management.
    MARKET CONDITION: Bear markets. It focuses only on the "pain" of drawdowns.
    """
    res = ta.ui(df["Close"], length=length)
    return res.tail(10).to_dict()
