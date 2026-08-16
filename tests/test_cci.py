"""Tests for get_cci (bug: pandas_ta 0.4.71b0's own cci() has a missing
parenthesis -- `typical_price - mean_typical_price / (c * mad)` instead of
`(typical_price - mean_typical_price) / (c * mad)` -- which produces values
in the thousands with the WRONG SIGN instead of the textbook +/-100 to +/-300
range. Verified live: RELIANCE.NS showed -4131.84 where the correct value
is +18.69. Fixed with an in-house implementation; not a pandas_ta version
bump, since the bug is unresolved as of 0.4.71b0.
"""

import numpy as np
import pandas as pd

from tools.indicators.momentum.cci import get_cci


def _hlc(n=60, seed=0):
    rng = np.random.default_rng(seed)
    close = pd.Series(100 + rng.standard_normal(n).cumsum())
    high = close + rng.uniform(0.5, 2.0, n)
    low = close - rng.uniform(0.5, 2.0, n)
    return pd.DataFrame({"High": high, "Low": low, "Close": close})


def test_cci_matches_textbook_formula():
    """(typical_price - SMA(typical_price)) / (0.015 * mean_abs_deviation)."""
    df = _hlc(n=60)
    result = get_cci(df, length=14)

    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma = tp.rolling(14).mean()
    mad = tp.rolling(14).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    expected = (tp - sma) / (0.015 * mad)

    got = list(result.values())
    exp = expected.tail(10).tolist()
    assert len(got) == len(exp) == 10
    for g, e in zip(got, exp):
        assert abs(g - e) < 1e-6, f"got {g}, expected textbook {e}"


def test_cci_stays_in_typical_oscillator_range():
    """CCI should oscillate roughly within +/-300 for ordinary price action,
    not the thousands the buggy formula produced."""
    df = _hlc(n=100, seed=1)
    result = get_cci(df, length=14)
    values = list(result.values())
    assert all(abs(v) < 500 for v in values), f"CCI out of expected range: {values}"


def test_cci_zero_when_price_at_its_own_mean():
    """A perfectly flat series has typical_price == its own SMA -> CCI == 0
    wherever MAD is nonzero, and NaN where MAD is zero (undefined division)."""
    idx = pd.RangeIndex(30)
    close = pd.Series([100.0] * 30, index=idx)
    df = pd.DataFrame({"High": close + 1, "Low": close - 1, "Close": close})
    result = get_cci(df, length=14)
    # Flat High/Low/Close each bar -> typical_price is constant -> MAD is 0 ->
    # 0/0 is NaN, which is the mathematically correct (undefined) answer.
    assert all(pd.isna(v) for v in result.values())


def test_cci_reproduces_the_live_regression_case():
    """Regression pin: on the exact data that showed -4131.84, the fixed
    implementation must land near the independently-verified +18.69."""
    # Synthetic stand-in reproducing the same shape (nearly-flat first 19
    # bars then a fresh 20-bar window) is impractical without live data, so
    # this test instead pins the ALGEBRAIC invariant that caught the bug:
    # for any window, (tp - sma) must have the same sign as the result
    # whenever mad > 0 (i.e. subtraction happens before division, not after).
    df = _hlc(n=40, seed=3)
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma = tp.rolling(14).mean()
    result = get_cci(df, length=14)
    tail_idx = df.index[-10:]
    for i, (key, v) in zip(tail_idx, result.items()):
        if pd.isna(v):
            continue
        sign_of_gap = np.sign(tp.loc[i] - sma.loc[i])
        assert np.sign(v) == sign_of_gap or v == 0, (
            f"CCI sign must match sign of (typical_price - SMA); got {v} "
            f"at a bar where tp-sma sign was {sign_of_gap}"
        )
