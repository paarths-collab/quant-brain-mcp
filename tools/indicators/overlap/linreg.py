import pandas_ta as ta


def get_linreg(df, length=14):
    """
    STRATEGY: Best fit line for price.
    WHEN TO USE: Identifying price exhaustion.
    SITUATION: When price moves significantly away from the LinReg line, expect a reversion to mean.
    """
    res = ta.linreg(df["Close"], length=length)
    return res.tail(10).to_dict()
