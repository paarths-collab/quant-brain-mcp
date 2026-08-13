"""Tests for the explicit 38-indicator allowlist and run_group helper."""

from unittest.mock import patch

import pandas as pd
import pytest

from core.indicator_registry import INDICATOR_GROUPS, iter_all_indicators, run_group

EXPECTED_GROUP_SIZES = {
    "momentum": 8,
    "technical_levels": 8,
    "trend": 6,
    "volatility": 6,
    "volume": 5,
    "statistics": 5,
}


def _fake_df():
    idx = pd.date_range("2024-01-01", periods=60, freq="D")
    base = pd.Series(range(100, 160), index=idx, dtype=float)
    return pd.DataFrame(
        {
            "Open": base,
            "High": base + 1.0,
            "Low": base - 1.0,
            "Close": base + 0.5,
            "Volume": 1_000_000,
        }
    )


def test_exactly_38_indicators_in_6_groups():
    assert set(INDICATOR_GROUPS) == set(EXPECTED_GROUP_SIZES)
    for group, size in EXPECTED_GROUP_SIZES.items():
        assert len(INDICATOR_GROUPS[group]["indicators"]) == size, group
    assert len(list(iter_all_indicators())) == 38


def test_aroon_is_trend_canonical():
    module_path, func_name = INDICATOR_GROUPS["trend"]["indicators"]["aroon"]
    assert module_path == "tools.indicators.trend.aroon"
    assert func_name == "get_aroon"
    assert "aroon" not in INDICATOR_GROUPS["momentum"]["indicators"]


def test_every_entry_resolves_to_a_callable():
    from core.indicator_registry import _resolve

    for key, module_path, func_name, _group in iter_all_indicators():
        func = _resolve(module_path, func_name)
        assert callable(func), f"{key} -> {module_path}.{func_name}"


def test_run_group_all_indicators_and_fetches_once():
    df = _fake_df()
    with patch("core.data_loader.fetch_data", return_value=(df, None)) as mock_fetch:
        result = run_group("momentum", "AAPL")
    assert mock_fetch.call_count == 1
    assert result["ticker"] == "AAPL"
    assert result["group"] == "momentum"
    assert set(result["indicators"]) == set(INDICATOR_GROUPS["momentum"]["indicators"])
    assert result["unknown_indicators"] == []


def test_run_group_subset_and_unknown_keys():
    df = _fake_df()
    with patch("core.data_loader.fetch_data", return_value=(df, None)):
        result = run_group("momentum", "AAPL", indicators=["RSI", "macd", "nope"])
    assert set(result["indicators"]) == {"rsi", "macd"}
    assert result["unknown_indicators"] == ["nope"]


def test_run_group_isolates_indicator_failure():
    df = _fake_df()
    boom = {"rsi": ("tests.test_indicator_registry", "_explode")}
    good = INDICATOR_GROUPS["momentum"]["indicators"]["macd"]
    patched = {**INDICATOR_GROUPS["momentum"], "indicators": {"rsi": boom["rsi"], "macd": good}}
    with patch("core.data_loader.fetch_data", return_value=(df, None)), patch.dict(
        INDICATOR_GROUPS, {"momentum": patched}
    ):
        result = run_group("momentum", "AAPL")
    assert "error" in result["indicators"]["rsi"]
    assert "error" not in result["indicators"]["macd"]


def _explode(df):
    raise RuntimeError("synthetic indicator failure")


def test_run_group_fetch_error_short_circuits():
    with patch("core.data_loader.fetch_data", return_value=(None, "no data for ticker")):
        result = run_group("volume", "BADTICKER")
    assert result["error"] == "no data for ticker"
    assert result["indicators"] == {}


def test_run_group_unknown_group_raises():
    with pytest.raises(KeyError):
        run_group("wrong_group", "AAPL")
