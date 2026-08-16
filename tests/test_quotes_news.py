"""Tests for get_quotes (delayed-quote snapshot) and get_ticker_news.

Design constraints these tests pin down:
- Quotes must carry an explicit as_of timestamp and a data-delay disclosure
  (NSE quotes are ~15min delayed on Yahoo; undisclosed staleness destroys
  trader trust, disclosed staleness is fine).
- One failing ticker must not take down the whole batch.
- News must come from yfinance's news API (no scraping), and degrade to an
  empty list, not an error, when a ticker has no coverage.
"""

from unittest.mock import MagicMock, patch

import pytest

from tools.trading.quotes import get_quotes
from tools.trading.news import get_ticker_news


class _FakeFastInfo:
    _DATA = {
        "lastPrice": 1310.0,
        "previousClose": 1317.0,
        "dayHigh": 1317.5,
        "dayLow": 1301.5,
        "yearHigh": 1611.8,
        "yearLow": 1249.8,
        "lastVolume": 10_497_358,
        "threeMonthAverageVolume": 13_780_448,
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "exchange": "NSI",
    }

    def __getitem__(self, key):
        return self._DATA[key]


class _ExplodingFastInfo:
    def __getitem__(self, key):
        raise KeyError(key)


def _fake_ticker(fast_info):
    t = MagicMock()
    t.fast_info = fast_info
    return t


# ------------------------------- quotes -------------------------------


def test_quote_has_price_change_and_ranges():
    with patch("yfinance.Ticker", return_value=_fake_ticker(_FakeFastInfo())):
        result = get_quotes(["RELIANCE.NS"])

    q = result["quotes"]["RELIANCE.NS"]
    assert q["last_price"] == 1310.0
    assert q["previous_close"] == 1317.0
    assert q["day_change_pct"] == pytest.approx(-0.53, abs=0.01)
    assert q["day_range"] == {"low": 1301.5, "high": 1317.5}
    assert q["52w_range"] == {"low": 1249.8, "high": 1611.8}
    assert q["currency"] == "INR"
    # position within the 52w range: (1310-1249.8)/(1611.8-1249.8) ~ 16.6%
    assert q["pct_of_52w_range"] == pytest.approx(16.6, abs=0.5)


def test_quote_volume_vs_average():
    with patch("yfinance.Ticker", return_value=_fake_ticker(_FakeFastInfo())):
        q = get_quotes(["RELIANCE.NS"])["quotes"]["RELIANCE.NS"]
    assert q["volume"] == 10_497_358
    assert q["volume_vs_3mo_avg"] == pytest.approx(0.76, abs=0.01)


def test_quote_discloses_delay_and_as_of():
    with patch("yfinance.Ticker", return_value=_fake_ticker(_FakeFastInfo())):
        result = get_quotes(["RELIANCE.NS"])
    assert "as_of" in result
    assert "delayed" in result["data_delay_note"].lower()
    assert "15" in result["data_delay_note"]  # NSE ~15min delay mentioned


def test_one_bad_ticker_does_not_break_the_batch():
    def ticker_side_effect(symbol):
        if symbol == "BADTICKER":
            return _fake_ticker(_ExplodingFastInfo())
        return _fake_ticker(_FakeFastInfo())

    with patch("yfinance.Ticker", side_effect=ticker_side_effect):
        result = get_quotes(["RELIANCE.NS", "BADTICKER"])

    assert result["quotes"]["RELIANCE.NS"]["last_price"] == 1310.0
    assert "error" in result["quotes"]["BADTICKER"]


def test_tickers_normalized_and_deduped():
    with patch("yfinance.Ticker", return_value=_fake_ticker(_FakeFastInfo())) as mock_t:
        result = get_quotes([" reliance.ns ", "RELIANCE.NS"])
    assert list(result["quotes"].keys()) == ["RELIANCE.NS"]
    assert mock_t.call_count == 1


def test_empty_ticker_list_is_clean_error():
    result = get_quotes([])
    assert "error" in result


def test_zero_previous_close_no_division_crash():
    class _ZeroPrev(_FakeFastInfo):
        _DATA = {**_FakeFastInfo._DATA, "previousClose": 0}

    with patch("yfinance.Ticker", return_value=_fake_ticker(_ZeroPrev())):
        q = get_quotes(["X"])["quotes"]["X"]
    assert q["day_change_pct"] is None


# ------------------------------- news -------------------------------


def _fake_news_item(title="RIL Q1 beats estimates", ago_hours=5):
    return {
        "content": {
            "title": title,
            "pubDate": "2026-08-16T09:30:00Z",
            "provider": {"displayName": "Reuters"},
            "canonicalUrl": {"url": "https://example.com/article"},
            "summary": "Reliance Industries reported...",
        }
    }


def test_news_returns_structured_headlines():
    t = MagicMock()
    t.news = [_fake_news_item(), _fake_news_item("Jio subscriber growth")]
    with patch("yfinance.Ticker", return_value=t):
        result = get_ticker_news("RELIANCE.NS", limit=5)

    assert result["ticker"] == "RELIANCE.NS"
    assert len(result["articles"]) == 2
    a = result["articles"][0]
    assert a["title"] == "RIL Q1 beats estimates"
    assert a["publisher"] == "Reuters"
    assert a["url"] == "https://example.com/article"
    assert a["published_at"] == "2026-08-16T09:30:00Z"


def test_news_respects_limit():
    t = MagicMock()
    t.news = [_fake_news_item(f"headline {i}") for i in range(10)]
    with patch("yfinance.Ticker", return_value=t):
        result = get_ticker_news("AAPL", limit=3)
    assert len(result["articles"]) == 3


def test_news_empty_coverage_is_empty_list_not_error():
    t = MagicMock()
    t.news = []
    with patch("yfinance.Ticker", return_value=t):
        result = get_ticker_news("OBSCURE.NS")
    assert result["articles"] == []
    assert "error" not in result


def test_news_malformed_item_skipped_not_fatal():
    t = MagicMock()
    t.news = [{"content": None}, _fake_news_item("good one")]
    with patch("yfinance.Ticker", return_value=t):
        result = get_ticker_news("AAPL")
    assert len(result["articles"]) == 1
    assert result["articles"][0]["title"] == "good one"


def test_news_fetch_failure_is_clean_error():
    with patch("yfinance.Ticker", side_effect=RuntimeError("network down")):
        result = get_ticker_news("AAPL")
    assert "error" in result
