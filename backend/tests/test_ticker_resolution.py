from backend.engine.pipeline import resolve_ticker_and_market, format_ticker_for_yfinance


def test_resolve_ticker_from_query_us():
    ticker, market = resolve_ticker_and_market("analyze NVDA", ticker=None, market=None)
    assert ticker == "NVDA"
    assert market == "us"


def test_resolve_ticker_from_query_india_and_formatting():
    ticker, market = resolve_ticker_and_market("analyze RELIANCE", ticker=None, market="in")
    assert ticker == "RELIANCE"
    assert market == "india"
    assert format_ticker_for_yfinance(ticker, market) == "RELIANCE.NS"


def test_discovery_query_does_not_force_single_ticker():
    ticker, market = resolve_ticker_and_market("Find me top AI stocks", ticker=None, market=None)
    assert ticker is None
    assert market == "us"


def test_explicit_ticker_overrides_query():
    ticker, market = resolve_ticker_and_market("analyze NVDA", ticker="TSLA", market=None)
    assert ticker == "TSLA"
    assert market == "us"

