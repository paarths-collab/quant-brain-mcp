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


def test_metadata_reports_actual_defaults_and_daily_bar_limitations():
    df = _fake_df()
    df.attrs.update(resolved_ticker="AAPL", retrieved_at="2026-01-01T12:00:00+00:00")
    with patch("core.data_loader.fetch_data", return_value=(df, None)):
        result = run_group("momentum", "AAPL", period="6mo")
    metadata = result["metadata"]
    assert metadata["history_period"] == "6mo"
    assert metadata["interval"] == "1d"
    assert metadata["input_rows"] == 60
    assert metadata["data_start"] == str(df.index.min())
    assert metadata["data_end"] == str(df.index.max())
    assert metadata["index_timezone"] is None
    assert metadata["retrieved_at"] == df.attrs["retrieved_at"]
    assert metadata["resolved_ticker"] == "AAPL"
    assert metadata["market_timestamp"] is None
    assert metadata["latest_bar_complete"] is None
    assert metadata["freshness"] == "unknown"
    assert metadata["adjustment"]["auto_adjust"] is True
    assert metadata["engine_versions"]["pandas-ta"]
    # Wrapper supplies RSI length, pandas-ta supplies TSI periods and Stoch smoothing.
    calculations = result["indicator_metadata"]
    assert calculations["rsi"]["parameters"]["length"] == 14
    assert calculations["stoch"]["parameters"]["smooth_k"] == 3
    assert calculations["tsi"]["parameters"]["signal"] == 13
    assert calculations["rsi"]["window_unit"] == "bars"
    assert calculations["rsi"]["status"] == "ok"


def test_metadata_preserves_timezone_without_inventing_exchange_close():
    df = _fake_df()
    df.index = df.index.tz_localize("Asia/Kolkata")
    with patch("core.data_loader.fetch_data", return_value=(df, None)):
        result = run_group("momentum", "EXAMPLE.NS", indicators=["rsi"])
    assert result["metadata"]["index_timezone"] == "Asia/Kolkata"
    assert result["metadata"]["market_status"] == "unknown"
    assert result["metadata"]["retrieved_at"] is None


def test_every_curated_indicator_has_metadata_and_valid_json():
    import json
    from core.indicator_metadata import LIBRARY_DEFAULTS, UNITS
    keys = {key for key, *_ in iter_all_indicators()}
    assert keys == set(LIBRARY_DEFAULTS) == set(UNITS)
    df = _fake_df()
    for group in INDICATOR_GROUPS:
        with patch("core.data_loader.fetch_data", return_value=(df, None)):
            result = run_group(group, "AAPL")
        json.dumps(result, allow_nan=False)
        for key, metadata in result["indicator_metadata"].items():
            assert "parameters" in metadata, (key, result["indicators"][key])
            assert metadata["output_units"]
            assert metadata["status"] in {"ok", "error"}
            if metadata["status"] == "ok":
                assert metadata["finite_output_values"] > 0


def test_all_null_output_is_an_explicit_error_and_does_not_hide_siblings():
    df = _fake_df()
    from core.indicator_registry import _resolve
    real_resolve = _resolve

    def resolve(module, function):
        if function == "get_zigzag":
            return lambda data: {"pivot": {str(data.index[-1]): float("nan")}}
        return real_resolve(module, function)

    with patch("core.data_loader.fetch_data", return_value=(df, None)), patch(
        "core.indicator_registry._resolve", side_effect=resolve
    ):
        result = run_group("trend", "AAPL", indicators=["zigzag", "aroon"])
    assert "No finite values" in result["indicators"]["zigzag"]["error"]
    assert result["indicator_metadata"]["zigzag"]["status"] == "error"
    assert result["indicator_metadata"]["zigzag"]["finite_output_values"] == 0
    assert result["indicator_metadata"]["aroon"]["status"] == "ok"


def test_empty_indicator_output_does_not_report_success():
    with patch("core.data_loader.fetch_data", return_value=(_fake_df(), None)), patch(
        "core.indicator_registry._resolve", return_value=lambda df: {}
    ):
        result = run_group("momentum", "AAPL", indicators=["rsi"])
    assert "error" in result["indicators"]["rsi"]


def test_custom_band_settings_reach_library_and_change_results():
    import numpy as np
    from tools.indicators.volatility.bbands import get_bbands
    from tools.indicators.volatility.donchian import get_donchian
    df = _fake_df()
    narrow = get_bbands(df, length=20, std=1)
    wide = get_bbands(df, length=20, std=3)
    def latest_prefix(result, prefix):
        return list(next(v for k, v in result.items() if k.startswith(prefix)).values())[-1]
    center = latest_prefix(narrow, "BBM")
    assert np.isclose(latest_prefix(wide, "BBU") - center,
                      3 * (latest_prefix(narrow, "BBU") - center))
    # The old wrapper sent an ignored `length` kwarg, always producing a 20-bar channel.
    channel = get_donchian(df, length=5)
    assert np.isclose(latest_prefix(channel, "DCL"), df.Low.tail(5).min())
    assert np.isclose(latest_prefix(channel, "DCU"), df.High.tail(5).max())


def test_history_loader_records_retrieval_time_and_resolved_symbol():
    from datetime import datetime
    from core.data_loader import resolve_ticker
    df = _fake_df()
    with patch("core.data_loader.yf.download", side_effect=[pd.DataFrame(), df]) as download:
        history, error, resolved = resolve_ticker("example", period="6mo")
    assert error is None
    assert resolved == history.attrs["resolved_ticker"] == "EXAMPLE.NS"
    assert datetime.fromisoformat(history.attrs["retrieved_at"]).tzinfo is not None
    assert download.call_args.kwargs["auto_adjust"] is True
    assert download.call_args.kwargs["interval"] == "1d"
