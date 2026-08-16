"""Regression tests for two correctness bugs:

1. RSI warmup was backfilled with future values (lookahead bias).
2. inf/NaN floats serialized to invalid JSON (Infinity/NaN tokens).
"""

import json
import math

import numpy as np
import pandas as pd

from tools.strategies.rsi_mean_reversion import _wilder_rsi
from utils.serializer import serialize_output


# --------------------------- RSI lookahead ---------------------------


def _noisy_close(n=60, seed=42):
    rng = np.random.default_rng(seed)
    return pd.Series(100 + rng.standard_normal(n).cumsum())


def test_rsi_warmup_is_nan_not_backfilled():
    """Bars before the lookback is satisfied must stay NaN, not inherit future values."""
    close = _noisy_close()
    rsi = _wilder_rsi(close, length=14)
    warmup = rsi.iloc[:13]
    assert warmup.isna().all(), "warmup bars must be NaN (no lookahead backfill)"


def test_rsi_warmup_does_not_equal_first_real_value():
    """The specific lookahead symptom: warmup == first legitimate value."""
    close = _noisy_close()
    rsi = _wilder_rsi(close, length=14)
    first_real = rsi.iloc[13]
    assert not (rsi.iloc[:13] == first_real).any()


def test_rsi_produces_no_signals_during_warmup():
    """NaN comparisons are False, so no entries/exits can fire before RSI exists."""
    close = _noisy_close()
    rsi = _wilder_rsi(close, length=14)
    entries = rsi < 30
    exits = rsi > 70
    assert not entries.iloc[:13].any()
    assert not exits.iloc[:13].any()


def test_rsi_all_gains_is_100_not_nan():
    """A monotonically rising series has no losses -> RSI is 100 by definition."""
    close = pd.Series(np.linspace(100, 150, 60))
    rsi = _wilder_rsi(close, length=14)
    assert rsi.iloc[-1] == 100.0, f"expected 100, got {rsi.iloc[-1]}"
    assert not rsi.iloc[14:].isna().any()


def test_rsi_flat_series_is_neutral():
    """A perfectly flat series has no gains and no losses -> neutral 50."""
    close = pd.Series([100.0] * 60)
    rsi = _wilder_rsi(close, length=14)
    assert rsi.iloc[-1] == 50.0


def test_rsi_values_stay_in_range():
    close = _noisy_close(200, seed=7)
    rsi = _wilder_rsi(close, length=14).dropna()
    assert len(rsi) > 0
    assert rsi.between(0, 100).all()


# --------------------------- JSON safety ---------------------------


def _is_strict_json(text: str) -> bool:
    """True only if the text parses without Infinity/NaN constants (JS-compatible)."""
    def _reject(token):
        raise ValueError(token)

    try:
        json.loads(text, parse_constant=_reject)
        return True
    except ValueError:
        return False


def test_numpy_inf_becomes_none():
    assert serialize_output(np.float64(np.inf)) is None
    assert serialize_output(np.float64(-np.inf)) is None


def test_numpy_nan_becomes_none():
    assert serialize_output(np.float64(np.nan)) is None


def test_native_float_inf_and_nan_become_none():
    assert serialize_output(float("inf")) is None
    assert serialize_output(float("nan")) is None


def test_finite_floats_are_preserved():
    assert serialize_output(np.float64(1.5)) == 1.5
    assert serialize_output(0.0) == 0.0
    assert serialize_output(-42.25) == -42.25


def test_backtest_shaped_payload_is_strict_json():
    """A backtest with zero losing trades yields inf profit_factor and NaN sharpe."""
    payload = serialize_output(
        {
            "strategy_name": "SMA Crossover",
            "profit_factor": np.float64(np.inf),
            "sharpe_ratio": np.float64(np.nan),
            "total_trades": np.int64(3),
            "total_return": "12.00%",
        }
    )
    text = json.dumps(payload)
    assert "Infinity" not in text and "NaN" not in text
    assert _is_strict_json(text)
    assert payload["profit_factor"] is None
    assert payload["sharpe_ratio"] is None
    assert payload["total_trades"] == 3


def test_nested_structures_are_sanitized():
    payload = serialize_output(
        {"a": [np.float64(np.inf), {"b": float("nan")}], "c": pd.Series([np.inf, 1.0])}
    )
    text = json.dumps(payload)
    assert _is_strict_json(text)
    assert payload["a"][0] is None
    assert payload["a"][1]["b"] is None


def test_integers_and_bools_unaffected():
    out = serialize_output({"i": np.int64(7), "b": np.bool_(True)})
    assert out["i"] == 7 and isinstance(out["i"], int)
    assert out["b"] is True
