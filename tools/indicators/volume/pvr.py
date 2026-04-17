import pandas_ta as ta


def get_pvr(df):
    """
    STRATEGY: Ranks stocks based on price and volume interaction.
    WHEN TO USE: Comparing stocks within a portfolio.
    MARKET CONDITION: Relative strength analysis.
    """
    res = ta.pvr(df["Close"], df["Volume"])
    return res.tail(10).to_dict()
