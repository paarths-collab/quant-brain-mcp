"""Symbols are validated against an injectable instrument resolver before any job exists."""
import pytest

from core.research_service import ResearchService, default_instrument_resolver
from core.research_store import ResearchStore
from tests.research_fakes import FakeMarketData, ScriptedRuntime

pytestmark = pytest.mark.usefixtures("no_live_network")


@pytest.fixture
def make(tmp_path):
    created = []

    def build(market, **kwargs):
        service = ResearchService(ResearchStore(tmp_path / "jobs.sqlite3"), ScriptedRuntime,
                                  instrument_resolver=market, timeout=60, **kwargs)
        created.append(service)
        return service

    yield build
    for service in created:
        service.close()


def assert_nothing_left_behind(service):
    assert service._executor is None            # no worker thread was started
    assert not service.store.path.exists()       # no database, so no orphaned job row
    assert not service._futures and not service._running


@pytest.mark.parametrize("tickers,message", [
    (["NOSUCHCO"], r"Unknown NSE symbol\(s\): NOSUCHCO\.NS"),
    (["TCS", "NOSUCHCO"], r"NOSUCHCO\.NS"),
    (["TCS.NS", "BADONE", "WORSE"], r"BADONE\.NS, WORSE\.NS"),
])
def test_unknown_symbol_is_rejected_before_a_job_exists(make, tickers, message):
    market = FakeMarketData()
    service = make(market)
    with pytest.raises(ValueError, match=message) as error:
        service.start("alice", "Review", tickers)
    assert "check the spelling" in str(error.value).lower()
    assert_nothing_left_behind(service)


def test_known_symbols_are_not_named_in_the_rejection(make):
    service = make(FakeMarketData())
    with pytest.raises(ValueError) as error:
        service.start("alice", "Review", ["WIPRO", "NOSUCHCO"])
    assert "WIPRO" not in str(error.value)


def test_non_nse_listing_and_non_equity_are_unsupported(make):
    market = FakeMarketData(unsupported={
        "BSEONLY.NS": {"symbol": "BSEONLY.NS", "exchange": "BSE", "quote_type": "EQUITY"},
        "NIFTYFUT.NS": {"symbol": "NIFTYFUT.NS", "exchange": "NSE", "quote_type": "FUTURE"},
    })
    service = make(market)
    with pytest.raises(ValueError, match="Unsupported instrument") as error:
        service.start("alice", "Review", ["BSEONLY", "NIFTYFUT", "TCS"])
    assert "BSEONLY.NS (listed on BSE, not NSE)" in str(error.value)
    assert "NIFTYFUT.NS (FUTURE, not an equity)" in str(error.value)
    assert_nothing_left_behind(service)


def test_lookup_failure_is_reported_as_unverifiable_not_unknown_and_leaks_nothing(make):
    service = make(FakeMarketData(failing={"INFY.NS"}))
    with pytest.raises(ValueError, match="Could not verify symbol") as error:
        service.start("alice", "Review", ["INFY", "TCS"])
    text = str(error.value)
    assert "INFY.NS" in text and "Unknown" not in text
    assert "SECRET_PRIVATE_VALUE" not in text and "provider.example" not in text
    assert_nothing_left_behind(service)


def test_all_problems_are_reported_together(make):
    market = FakeMarketData(unsupported={"BSEONLY.NS": {"exchange": "BSE"}}, failing={"INFY.NS"})
    service = make(market)
    with pytest.raises(ValueError) as error:
        service.start("alice", "Review", ["NOSUCHCO", "BSEONLY", "INFY"])
    text = str(error.value)
    assert "NOSUCHCO.NS" in text and "BSEONLY.NS" in text and "INFY.NS" in text


def test_resolver_sees_each_normalized_symbol_once_and_valid_jobs_start(make):
    market = FakeMarketData()
    service = make(market)
    job = service.start("alice", "Review", ["tcs", "TCS.NS", " infy.ns "], "quick")
    assert market.calls == ["TCS.NS", "INFY.NS"]
    assert job["tickers"] == ["TCS.NS", "INFY.NS"]


def test_format_errors_never_reach_the_market_data_lookup(make):
    market = FakeMarketData()
    service = make(market)
    for bad in (["../secrets"], ["TCS.BO"], [], ["A"] * 6, "TCS"):
        with pytest.raises(ValueError):
            service.start("alice", "Review", bad)
    assert market.calls == []


def test_unauthenticated_or_invalid_request_does_not_spend_a_lookup(make):
    market = FakeMarketData()
    service = make(market)
    with pytest.raises(ValueError, match="Authentication"):
        service.start("", "Review", ["TCS"])
    with pytest.raises(ValueError, match="Question"):
        service.start("alice", " ", ["TCS"])
    assert market.calls == []


def test_rejected_start_does_not_consume_queue_capacity(make):
    service = make(FakeMarketData())
    for _ in range(5):
        with pytest.raises(ValueError):
            service.start("alice", "Review", ["NOSUCHCO"])
    assert service.start("alice", "Review", ["TCS"], "quick")["status"] == "queued"
    assert service.store.active_count("alice") <= 1


def test_default_resolver_distinguishes_unknown_from_provider_failure(monkeypatch):
    from core.research_service import InstrumentLookupError
    calls = []
    results = {
        "TCS.NS": object(),
        "NOSUCHCO.NS": {"error": "No data found for ticker 'NOSUCHCO.NS'. Check if the symbol is correct"},
        "INFY.NS": {"error": "Failed to fetch data for INFY.NS: https://x.example/?token=SECRET"},
    }
    monkeypatch.setattr("core.data_loader.fetch_stock_data", lambda symbol, period: calls.append(symbol) or results[symbol])
    assert default_instrument_resolver("TCS.NS")["exchange"] == "NSE"
    assert default_instrument_resolver("NOSUCHCO.NS") is None
    with pytest.raises(InstrumentLookupError) as error:
        default_instrument_resolver("INFY.NS")
    assert "SECRET" not in str(error.value)
    assert calls == ["TCS.NS", "NOSUCHCO.NS", "INFY.NS"]


def test_test_guard_blocks_live_calls():
    import socket
    with pytest.raises(AssertionError, match="live"):
        socket.create_connection(("93.184.216.34", 80), timeout=1)
    from core.data_loader import fetch_stock_data
    with pytest.raises(AssertionError, match="live"):
        fetch_stock_data("TCS.NS")
