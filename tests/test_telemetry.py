"""Tests for telemetry instrumentation, session derivation, and the writer."""

import inspect
import queue
import time
from unittest.mock import MagicMock, patch

import pytest

from core import telemetry
from core.telemetry import Event, derive_session_id, instrument


@pytest.fixture(autouse=True)
def _reset_writer(monkeypatch):
    """Each test gets a fresh, disabled writer unless it opts in."""
    monkeypatch.setattr(telemetry, "_writer", None)
    yield
    monkeypatch.setattr(telemetry, "_writer", None)


def _sample_tool(ticker: str, amount: float = 10000) -> dict:
    """Sample docstring preserved."""
    return {"ok": ticker, "amount": amount}


def test_instrument_preserves_name_doc_and_signature():
    wrapped = instrument(_sample_tool, "backtest")
    assert wrapped.__name__ == "_sample_tool"
    assert "Sample docstring" in wrapped.__doc__
    assert str(inspect.signature(wrapped)) == str(inspect.signature(_sample_tool))


def test_instrument_records_success_event():
    events = []
    with patch.object(telemetry, "record", events.append):
        result = instrument(_sample_tool, "backtest")("AAPL")
    assert result == {"ok": "AAPL", "amount": 10000}
    assert len(events) == 1
    ev = events[0]
    assert ev.tool_name == "_sample_tool"
    assert ev.tool_category == "backtest"
    assert ev.success is True
    assert ev.error is None
    assert ev.duration_ms >= 0


def test_instrument_soft_error_dict_counts_as_failure():
    def soft_fail(ticker: str) -> dict:
        return {"error": "no data"}

    events = []
    with patch.object(telemetry, "record", events.append):
        result = instrument(soft_fail, "indicator")("BAD")
    assert result == {"error": "no data"}
    assert events[0].success is False
    assert events[0].error == "no data"


def test_instrument_exception_recorded_and_reraised():
    def hard_fail(ticker: str) -> dict:
        raise ValueError("boom")

    events = []
    with patch.object(telemetry, "record", events.append):
        with pytest.raises(ValueError, match="boom"):
            instrument(hard_fail, "indicator")("BAD")
    assert events[0].success is False
    assert "boom" in events[0].error


def test_instrument_survives_broken_record():
    def broken_record(_ev):
        raise RuntimeError("telemetry down")

    with patch.object(telemetry, "record", broken_record):
        assert instrument(_sample_tool, "backtest")("AAPL")["ok"] == "AAPL"


def test_derive_session_id_without_context_is_unknown():
    assert derive_session_id(None) == "unknown"

    def exploding_context():
        raise LookupError("no active request")

    assert derive_session_id(exploding_context) == "unknown"


def test_derive_session_id_prefers_header_then_fingerprint():
    request = MagicMock()
    request.headers = {"mcp-session-id": "abc123"}
    ctx = MagicMock()
    ctx.request_context.request = request
    assert derive_session_id(lambda: ctx) == "abc123"

    request2 = MagicMock()
    request2.headers = {"user-agent": "claude/1.0"}
    request2.client.host = "10.0.0.5"
    ctx2 = MagicMock()
    ctx2.request_context.request = request2
    fp = derive_session_id(lambda: ctx2)
    assert fp.startswith("fp_") and len(fp) == 19
    # Deterministic for the same client.
    assert derive_session_id(lambda: ctx2) == fp


def test_record_is_noop_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    telemetry.record(
        Event("t", "indicator", "s", 1.0, True, None)
    )  # must not raise or create a writer thread
    assert telemetry._writer is not None
    assert telemetry._writer.enabled is False


def test_record_queue_full_drops_silently(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake")
    writer = telemetry.TelemetryWriter("postgresql://fake", start_thread=False)
    writer.queue = queue.Queue(maxsize=1)
    monkeypatch.setattr(telemetry, "_writer", writer)
    telemetry.record(Event("a", "indicator", "s", 1.0, True, None))
    telemetry.record(Event("b", "indicator", "s", 1.0, True, None))  # dropped
    assert writer.queue.qsize() == 1
    assert writer.dropped == 1
