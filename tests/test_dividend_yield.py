"""Test for bug C5: dividend yield inflated 100x in two nested fields.

yfinance's `dividendYield` already returns a percent (e.g. 2.42 for 2.42%),
but get_deep_fundamentals and get_company_info's `fundamentals` block both
multiplied it by 100 again, producing "242.00%" for a stock that actually
yields 2.42%. The top-level `dividend_yield` field was already correct and
is unaffected.
"""

from unittest.mock import MagicMock, patch

import pandas as pd

from tools.intelligence.company_profile import get_company_info, get_deep_fundamentals


def _fake_info(dividend_yield=2.42):
    return {
        "longName": "The Coca-Cola Company",
        "shortName": "Coca-Cola",
        "sector": "Consumer Defensive",
        "dividendYield": dividend_yield,
        "trailingPE": 25.0,
        "priceToBook": 10.0,
        "debtToEquity": 150.0,
        "returnOnEquity": 0.40,
        "marketCap": 260_000_000_000,
    }


def _fake_df():
    idx = pd.date_range("2024-01-01", periods=10, freq="B")
    return pd.DataFrame({"Close": 60.0}, index=idx)


def test_deep_fundamentals_dividend_yield_not_inflated():
    mock_ticker = MagicMock()
    mock_ticker.info = _fake_info()
    with patch("yfinance.Ticker", return_value=mock_ticker):
        result = get_deep_fundamentals("KO")
    assert result["Dividend_Yield"] == "2.42%"


def test_company_info_fundamentals_dividend_yield_not_inflated():
    mock_ticker = MagicMock()
    mock_ticker.info = _fake_info()
    with patch("yfinance.Ticker", return_value=mock_ticker), patch(
        "tools.intelligence.company_profile.fetch_data", return_value=(_fake_df(), None)
    ):
        result = get_company_info("KO")
    assert result["fundamentals"]["Dividend_Yield"] == "2.42%"
    assert result["deep_fundamentals"]["Dividend_Yield"] == "2.42%"


def test_all_three_dividend_fields_agree():
    """All three dividend fields must describe the SAME real-world yield."""
    mock_ticker = MagicMock()
    mock_ticker.info = _fake_info()
    with patch("yfinance.Ticker", return_value=mock_ticker), patch(
        "tools.intelligence.company_profile.fetch_data", return_value=(_fake_df(), None)
    ):
        result = get_company_info("KO")

    # dividend_yield is already a percent value (2.42 means "2.42%"), same
    # convention as the formatted fields -- no *100 conversion between them.
    top_level = result["dividend_yield"]
    fundamentals_pct = float(result["fundamentals"]["Dividend_Yield"].rstrip("%"))
    deep_pct = float(result["deep_fundamentals"]["Dividend_Yield"].rstrip("%"))

    assert abs(fundamentals_pct - top_level) < 0.01
    assert abs(deep_pct - top_level) < 0.01


def test_zero_dividend_stock_does_not_crash():
    mock_ticker = MagicMock()
    mock_ticker.info = _fake_info(dividend_yield=None)
    with patch("yfinance.Ticker", return_value=mock_ticker), patch(
        "tools.intelligence.company_profile.fetch_data", return_value=(_fake_df(), None)
    ):
        result = get_company_info("TSLA")
    assert result["fundamentals"]["Dividend_Yield"] == "0.00%"
