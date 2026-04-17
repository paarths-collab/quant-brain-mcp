import pandas_ta as ta


def get_mcgd(df, length=10):
    """
    STRATEGY: Adjusts itself to market speed automatically.
    WHEN TO USE: Dynamic support/resistance.
    SITUATION: It 'hugs' price closer than an EMA during rapid moves.
    """
    res = ta.mcgd(df["Close"], length=length)
    return res.tail(10).to_dict()
