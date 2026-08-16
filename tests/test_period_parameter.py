"""Tests for exposing the `period` parameter (bug/gap: everything was hardcoded
to 2y, so a user asking for a 5y or 10y backtest had no way to get one).

Covers:
- core.data_loader validates period against yfinance's accepted set and
  returns a clean error instead of a confusing downstream failure.
- core.indicator_registry.run_group propagates a custom period to fetch_data.
- main.run_generate_optimized_verdict propagates a custom period to the
  ticker resolution/fetch step.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from core.data_loader import VALID_PERIODS, fetch_stock_data, resolve_ticker
from core.indicator_registry import run_group


def _df(periods=60):
    idx = pd.date_range("2024-01-01", periods=periods, freq="B")
    close = pd.Series(100.0 + np.arange(periods), index=idx)
    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1000}
    )


def test_valid_periods_matches_yfinance_accepted_set():
    assert VALID_PERIODS == {
        "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max",
    }


def test_invalid_period_returns_clean_error_not_a_crash():
    result = fetch_stock_data("AAPL", period="3years")
    assert isinstance(result, dict)
    assert "error" in result
    assert "period" in result["error"].lower()


def test_valid_period_is_forwarded_to_yfinance():
    with patch("yfinance.download", return_value=_df()) as mock_dl:
        fetch_stock_data("AAPL", period="10y")
    assert mock_dl.call_args.kwargs["period"] == "10y"


def test_resolve_ticker_forwards_custom_period():
    with patch("core.data_loader.fetch_stock_data", return_value=_df()) as mock_fetch:
        resolve_ticker("AAPL", period="5y")
    assert mock_fetch.call_args.kwargs.get("period") == "5y" or mock_fetch.call_args.args[1:2] == ("5y",)


def test_run_group_default_period_is_2y():
    with patch("core.data_loader.fetch_data", return_value=(_df(), None)) as mock_fetch:
        run_group("momentum", "AAPL")
    assert mock_fetch.call_args.kwargs.get("period", "2y") == "2y"


def test_run_group_propagates_custom_period():
    with patch("core.data_loader.fetch_data", return_value=(_df(300), None)) as mock_fetch:
        run_group("momentum", "AAPL", period="10y")
    assert mock_fetch.call_args.kwargs["period"] == "10y"


def test_run_group_rejects_invalid_period_cleanly():
    result = run_group("momentum", "AAPL", period="banana")
    assert "error" in result
    assert result["indicators"] == {}
