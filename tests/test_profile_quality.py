from unittest.mock import MagicMock, patch
import pytest

from tools.intelligence.company_profile import get_company_info


def profile(info):
    ticker = MagicMock()
    ticker.info = info
    with patch("yfinance.Ticker", return_value=ticker) as factory:
        result = get_company_info("EXAMPLE.NS")
    assert factory.call_count == 1  # all nested fields use the same provider snapshot
    return result


def test_debt_units_preserve_legacy_percent_and_explicit_multiple():
    result = profile({"longName": "Example", "debtToEquity": 9.83})
    assert result["debt_to_equity_percent"] == 9.83
    assert result["debt_to_equity_ratio"] == pytest.approx(0.0983)
    assert result["fundamentals"]["Debt_To_Equity_Unit"] == "percent"
    assert result["deep_fundamentals"]["Debt_to_Equity_Unit"] == "percent"
    assert result["confidence"] is None
    assert result["valuation_as_of"] is None
    assert result["freshness_status"] == "unknown"
    assert result["retrieved_at"]


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), "bad"])
def test_missing_or_invalid_values_are_not_zero(value):
    result = profile({"longName": "Example", "debtToEquity": value,
                      "dividendYield": value, "returnOnEquity": value, "marketCap": value})
    assert result["debt_to_equity_ratio"] is None
    for key in ["Dividend_Yield", "ROE", "Market_Cap"]:
        assert result["fundamentals"][key] is None
        assert result["deep_fundamentals"][key] is None


def test_reported_zero_is_preserved():
    result = profile({"longName": "Example", "debtToEquity": 0, "dividendYield": 0})
    assert result["debt_to_equity_ratio"] == 0
    assert result["fundamentals"]["Dividend_Yield"] == "0.00%"


def test_empty_profile_is_error_not_confident_success():
    assert "error" in profile({})


def test_non_us_market_cap_not_assumed_usd():
    ticker = MagicMock(info={"longName": "Example", "currency": "GBP", "marketCap": 1e9})
    with patch("yfinance.Ticker", return_value=ticker):
        result = get_company_info("EXAMPLE.L")
    assert result["deep_fundamentals"]["Market_Cap"] == "1.00 B GBP"
