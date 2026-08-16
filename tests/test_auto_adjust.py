"""Tests for bug H11: auto_adjust=False excluded dividends from every return.

yf.download(auto_adjust=False) returns raw Close prices; total return
computed from raw Close silently ignores dividend payouts, understating
every return/Sharpe/alpha figure for dividend-paying stocks. Audit measured
an 8.91pp gap on XLE (36.71% vs 45.62% true total return) over 2 years.

Every downstream consumer in this codebase reads df["Close"] directly (no
code references "Adj Close"), so switching auto_adjust=True makes "Close"
the dividend/split-adjusted price everywhere with no other code changes
needed.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from core.data_loader import fetch_multi_data, fetch_stock_data


def _fake_yf_frame(periods=30):
    idx = pd.date_range("2024-01-01", periods=periods, freq="B")
    close = pd.Series(100.0 + np.arange(periods), index=idx)
    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1000}
    )


def test_fetch_stock_data_requests_auto_adjusted_prices():
    with patch("yfinance.download", return_value=_fake_yf_frame()) as mock_dl:
        fetch_stock_data("KO")
    assert mock_dl.call_args.kwargs["auto_adjust"] is True


def test_fetch_multi_data_requests_auto_adjusted_prices():
    frame = _fake_yf_frame()
    multi = pd.concat({"Close": frame["Close"]}, axis=1)
    with patch("yfinance.download", return_value=multi) as mock_dl:
        fetch_multi_data(["KO", "PEP"])
    assert mock_dl.call_args.kwargs["auto_adjust"] is True


def test_multiindex_columns_still_flatten_with_auto_adjust():
    """auto_adjust=True must not break the existing MultiIndex flattening path."""
    frame = _fake_yf_frame()
    multi_cols = pd.MultiIndex.from_product([frame.columns, ["KO"]])
    multi_df = frame.copy()
    multi_df.columns = multi_cols

    with patch("yfinance.download", return_value=multi_df):
        result = fetch_stock_data("KO")

    assert not isinstance(result, dict), f"expected a DataFrame, got error: {result}"
    assert not isinstance(result.columns, pd.MultiIndex)
    assert "Close" in result.columns


def test_dividend_paying_stock_total_return_includes_dividends_live():
    """Live smoke check: a known dividend payer's 2y total return must reflect
    dividends, not just raw price appreciation."""
    import yfinance as yf

    from core.data_loader import fetch_data

    raw = yf.download("KO", period="2y", auto_adjust=False, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    if raw.empty:
        return  # network unavailable in this environment; skip silently

    raw_return = float(raw["Close"].iloc[-1] / raw["Close"].iloc[0] - 1)

    df, err = fetch_data("KO")
    assert err is None and df is not None
    adjusted_return = float(df["Close"].iloc[-1] / df["Close"].iloc[0] - 1)

    # Adjusted (dividend-inclusive) total return must be >= raw price-only
    # return for a stock that pays a regular dividend and did not cut it.
    assert adjusted_return >= raw_return - 1e-9
    assert adjusted_return > raw_return, (
        f"expected dividend-adjusted return ({adjusted_return:.4f}) to exceed "
        f"raw price return ({raw_return:.4f}) for a dividend payer over 2 years"
    )
