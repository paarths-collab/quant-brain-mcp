import numpy as np


def get_cci(df, length=14, c=0.015):
    """Commodity Channel Index, computed in-house (not via pandas_ta).

    pandas_ta 0.4.71b0's cci() has a missing parenthesis:
        typical_price - mean_typical_price / (c * mad)
    instead of the textbook
        (typical_price - mean_typical_price) / (c * mad)
    Division binds tighter than subtraction, so the shipped formula divides
    only the mean by (c * mad) and then subtracts that from the raw typical
    price -- producing values in the thousands with the WRONG SIGN instead
    of the standard +/-100 to +/-300 oscillator range. Verified live:
    RELIANCE.NS showed -4131.84 where the correct value is +18.69.
    """
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    sma = typical_price.rolling(length).mean()
    mean_abs_deviation = typical_price.rolling(length).apply(
        lambda window: np.abs(window - window.mean()).mean(), raw=True
    )
    cci = (typical_price - sma) / (c * mean_abs_deviation)
    return cci.tail(10).to_dict()
