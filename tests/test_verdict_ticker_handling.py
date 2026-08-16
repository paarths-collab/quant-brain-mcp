"""Tests for run_generate_optimized_verdict's ticker handling.

Covers three bugs rooted in the same cause (raw ticker strings used as
dict keys instead of the resolved symbol that actually fetched data):

  C4 - "RELIANCE" (no suffix) was benchmarked against ^GSPC instead of
       ^NSEI, because the raw string never carried the ".NS" suffix that
       fetch_data resolved internally.
  H1 - a ticker that failed to fetch vanished from the result with no trace.
  H5 - "aapl" and "AAPL" became two separate portfolio assets instead of
       one, because dict keys were case-sensitive raw input.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd

from main import run_generate_optimized_verdict


def _ohlc(seed, periods=300, start=100.0):
    idx = pd.date_range("2023-01-02", periods=periods, freq="B")
    rng = np.random.default_rng(seed)
    close = pd.Series(start * np.exp(np.cumsum(rng.normal(0.0012, 0.010, periods))), index=idx)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": 1_000_000,
        }
    )


def _fake_fetch_data(seed_by_resolved):
    """Build a fetch_stock_data stub keyed by the RESOLVED (suffixed) symbol."""

    def _stub(ticker, period="2y", interval="1d"):
        if ticker in seed_by_resolved:
            return _ohlc(seed_by_resolved[ticker])
        return {"error": f"No data found for ticker '{ticker}'."}

    return _stub


def test_unsuffixed_indian_ticker_gets_correct_benchmark():
    """RELIANCE (no .NS) must be benchmarked against ^NSEI, not ^GSPC."""
    stub = _fake_fetch_data({"RELIANCE.NS": 1, "AAPL": 2, "^NSEI": 3, "^GSPC": 4})
    with patch("core.data_loader.fetch_stock_data", side_effect=stub):
        result = run_generate_optimized_verdict(["RELIANCE"], 10000, "mvo")

    assert "error" not in result
    assert result["intelligence_ticker"] == "RELIANCE.NS"
    assert result["benchmark_ticker"] == "^NSEI"


def test_case_variants_collapse_to_one_asset():
    """'aapl' and 'AAPL' must be treated as the SAME stock, not two assets."""
    stub = _fake_fetch_data({"AAPL": 1, "^GSPC": 2})
    with patch("core.data_loader.fetch_stock_data", side_effect=stub):
        result = run_generate_optimized_verdict(["aapl", "AAPL"], 10000, "mvo")

    assert "error" not in result
    weights = result["recommended_weights"]
    assert len(weights) == 1, f"expected one collapsed asset, got {weights}"
    assert "AAPL" in weights


def test_failed_ticker_is_visible_not_silently_dropped():
    """A ticker that fails to fetch must be reported, not vanish silently."""
    stub = _fake_fetch_data({"AAPL": 1, "MSFT": 2, "^GSPC": 3})
    with patch("core.data_loader.fetch_stock_data", side_effect=stub):
        result = run_generate_optimized_verdict(["AAPL", "MSFT", "NOTREAL"], 10000, "mvo")

    assert "error" not in result
    assert result["requested_tickers"] == ["AAPL", "MSFT", "NOTREAL"]
    assert set(result["included_tickers"]) == {"AAPL", "MSFT"}
    excluded = result["excluded_tickers"]
    assert len(excluded) == 1
    assert excluded[0]["ticker"] == "NOTREAL"
    assert "error" in excluded[0]


def test_all_tickers_included_when_all_succeed():
    stub = _fake_fetch_data({"AAPL": 1, "MSFT": 2, "^GSPC": 3})
    with patch("core.data_loader.fetch_stock_data", side_effect=stub):
        result = run_generate_optimized_verdict(["AAPL", "MSFT"], 10000, "mvo")

    assert result["excluded_tickers"] == []
    assert set(result["included_tickers"]) == {"AAPL", "MSFT"}
