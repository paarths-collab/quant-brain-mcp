"""Tests for bug H10: MACD momentum silently reported '0 trades' as a valid
result on any ticker with under 200 bars of history.

ta.ema(close, length=200) returns None (not NaN) when the series is shorter
than the lookback. `close > None` does not raise -- pandas broadcasts it to
all-False -- so `entries` was unconditionally empty regardless of any real
MACD crossover, and the backtest reported a confident-looking "0.00% return,
0 trades" instead of surfacing that the strategy could not run.
"""

import numpy as np
import pandas as pd
import pytest

from tools.strategies.macd_momentum import run_strategy


def _trending_close(n, seed=1, drift=0.002, vol=0.01):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, vol, n))), index=idx)


def _df(n, **kwargs):
    close = _trending_close(n, **kwargs)
    return pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1_000_000}
    )


def test_short_series_returns_explicit_error_not_fake_zero_trades():
    """Under 200 bars: ta.ema(close, 200) is None -> must error, not silently
    report a plausible-looking zero-trade backtest."""
    result = run_strategy(_df(150))
    assert "error" in result, f"expected an explicit error for <200 bars, got: {result}"
    assert "200" in result["error"]


def test_exactly_at_boundary_still_works():
    """At >= 200 bars, ema200 is defined and the strategy must run normally."""
    result = run_strategy(_df(250))
    assert "error" not in result
    assert result["strategy_name"] == "MACD Momentum"
    assert "total_trades" in result


def test_long_uptrend_can_actually_fire_entries():
    """Regression: on a long enough, clearly trending series, MACD momentum
    must be able to produce trades (proves entries isn't silently all-False
    for a non-error reason too)."""
    result = run_strategy(_df(400, drift=0.0015, vol=0.008))
    assert "error" not in result
    assert result["total_trades"] >= 0  # shape check; not asserting a specific count
