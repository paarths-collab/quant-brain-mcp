import pandas_ta as ta


def get_pvol(df):
    """
    STRATEGY: Simple multiplication of Price and Volume to see dollar flow.
    WHEN TO USE: Liquidity checks.
    MARKET CONDITION: Small-cap or mid-cap analysis (common in Indian market).
    """
    res = ta.pvol(df["Close"], df["Volume"])
    return res.tail(10).to_dict()
