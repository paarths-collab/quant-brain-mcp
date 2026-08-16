"""Tests for ticker resolution (core/data_loader.resolve_ticker).

Root cause fix for three bugs found in the audit:
  C4 - unsuffixed Indian tickers ("RELIANCE") kept their raw string as the
       dict key, so _infer_benchmark_ticker saw no ".NS"/".BO" suffix and
       benchmarked Indian data against the S&P 500.
  H1 - failed tickers were silently dropped with no trace in the response.
  H5 - "aapl" and "AAPL" were used as separate dict keys, splitting one
       stock into two "different" portfolio assets.

fetch_data's existing 2-tuple contract is unchanged (11 call sites depend on
it). resolve_ticker is a new function that performs the same probing and
additionally returns which symbol actually resolved.
"""

from unittest.mock import patch

import pandas as pd

from core.data_loader import fetch_data, resolve_ticker


def _df():
    idx = pd.date_range("2024-01-01", periods=30, freq="B")
    return pd.DataFrame(
        {"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1000},
        index=idx,
    )


def test_already_suffixed_ticker_resolves_to_itself():
    with patch("core.data_loader.fetch_stock_data", return_value=_df()) as mock:
        df, err, resolved = resolve_ticker("RELIANCE.NS")
    assert err is None
    assert resolved == "RELIANCE.NS"
    mock.assert_called_once()


def test_unsuffixed_indian_ticker_resolves_to_ns_suffix():
    """The bug: RELIANCE (no suffix) must resolve to RELIANCE.NS, not stay bare."""
    calls = []

    def fake_fetch(ticker, period="2y", interval="1d"):
        calls.append(ticker)
        if ticker == "RELIANCE":
            return {"error": "No data found for ticker 'RELIANCE'."}
        return _df()

    with patch("core.data_loader.fetch_stock_data", side_effect=fake_fetch):
        df, err, resolved = resolve_ticker("RELIANCE")

    assert err is None
    assert resolved == "RELIANCE.NS", "must resolve to the suffixed symbol that actually worked"
    assert calls == ["RELIANCE", "RELIANCE.NS"]


def test_us_ticker_resolves_to_itself_without_ns_retry():
    calls = []

    def fake_fetch(ticker, period="2y", interval="1d"):
        calls.append(ticker)
        return _df()

    with patch("core.data_loader.fetch_stock_data", side_effect=fake_fetch):
        df, err, resolved = resolve_ticker("AAPL")

    assert resolved == "AAPL"
    assert calls == ["AAPL"]


def test_case_variants_resolve_to_the_same_symbol():
    """The bug: 'aapl' and 'AAPL' must resolve identically so they collapse
    into one portfolio asset instead of two."""
    with patch("core.data_loader.fetch_stock_data", return_value=_df()):
        _, _, r1 = resolve_ticker("aapl")
        _, _, r2 = resolve_ticker("AAPL")
        _, _, r3 = resolve_ticker("  Aapl  ")
    assert r1 == r2 == r3 == "AAPL"


def test_unresolvable_ticker_returns_error_and_original_symbol():
    with patch(
        "core.data_loader.fetch_stock_data",
        return_value={"error": "No data found for ticker 'NOTREAL'."},
    ):
        df, err, resolved = resolve_ticker("NOTREAL")
    assert df is None
    assert err is not None
    assert resolved == "NOTREAL"


def test_fetch_data_contract_is_unchanged():
    """fetch_data must remain a strict 2-tuple for its 11 existing callers."""
    with patch("core.data_loader.fetch_stock_data", return_value=_df()):
        result = fetch_data("AAPL")
    assert len(result) == 2
    df, err = result
    assert err is None
    assert df is not None


def test_fetch_data_and_resolve_ticker_agree():
    def fake_fetch(ticker, period="2y", interval="1d"):
        if ticker == "RELIANCE":
            return {"error": "no data"}
        return _df()

    with patch("core.data_loader.fetch_stock_data", side_effect=fake_fetch):
        df_a, err_a = fetch_data("RELIANCE")
        df_b, err_b, resolved = resolve_ticker("RELIANCE")

    assert err_a == err_b
    assert (df_a is None) == (df_b is None)
    assert resolved == "RELIANCE.NS"
