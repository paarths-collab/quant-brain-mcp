"""Exercise real queue/workflow/storage with deterministic model boundaries."""
import asyncio
import threading
import time

import pytest

from core.research_service import ResearchService
from core.research_store import ResearchStore


class EmptyRuntime:
    async def run(self, role, prompt):
        return {"summary": "No reliable evidence in this test", "outcome": "insufficient_evidence"}


class WaitingRuntime:
    def __init__(self):
        self.started = threading.Event()
        self.cleaned = threading.Event()

    async def run(self, role, prompt):
        self.started.set()
        try:
            await asyncio.Event().wait()
        finally:
            self.cleaned.set()


@pytest.fixture
def service(tmp_path):
    instance = ResearchService(ResearchStore(tmp_path / "jobs.sqlite3"), EmptyRuntime, timeout=3)
    yield instance
    instance.close()


def wait_terminal(service, job_id, owner="alice"):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = service.status(owner, job_id)
        if result.get("status") in {"completed", "failed", "cancelled"}:
            return result
        time.sleep(0.01)
    pytest.fail("Research worker did not reach terminal state")


def start(service, owner="alice", **kwargs):
    return service.start(owner, kwargs.pop("question", "Review this company"), kwargs.pop("tickers", ["tcs", "TCS.NS"]), **kwargs)


def test_complete_persists_report_and_hides_other_owners(service):
    job = start(service)
    assert job["tickers"] == ["TCS.NS"]
    assert wait_terminal(service, job["id"])["status"] == "completed"
    report = service.report("alice", job["id"])
    assert report["report"]["outcome"] == "insufficient_evidence"
    assert report["report"]["market"] == "NSE"
    assert report["report"]["invocation_count"] == 6
    assert report["events"]
    assert "events" not in service.status("alice", job["id"])
    stored = ResearchStore(service.store.path).get("alice", job["id"])
    assert stored["report"] == report["report"]
    for method in (service.status, service.report, service.cancel):
        assert method("bob", job["id"]) == {"error": "Research job not found"}


@pytest.mark.parametrize("changes", [
    {"question": " "}, {"question": "x" * 12001}, {"question": None},
    {"depth": "endless"}, {"tickers": []}, {"tickers": ["TCS.BO"]},
    {"tickers": ["../secrets"]}, {"tickers": ["TCS"] * 6},
    {"tickers": None}, {"tickers": "TCS"}, {"tickers": [123]},
])
def test_invalid_request_rejected_before_worker_creation(service, changes):
    with pytest.raises(ValueError):
        start(service, **changes)
    assert service._executor is None
    assert not service.store.path.exists()


def test_owner_required(service):
    with pytest.raises(ValueError, match="Authentication"):
        start(service, owner="")


def test_cancel_running_cleans_up_runtime(service):
    runtime = WaitingRuntime()
    service.runtime_factory = lambda: runtime
    job = start(service)
    assert runtime.started.wait(2)
    assert service.cancel("alice", job["id"])["status"] == "cancelled"
    assert runtime.cleaned.wait(2)
    service.close()
    assert service.report("alice", job["id"])["report"] is None
    assert service.status("alice", job["id"])["status"] == "cancelled"


def test_worker_lock_prevents_second_service_and_releases(service):
    first = start(service)
    wait_terminal(service, first["id"])
    other = ResearchService(ResearchStore(service.store.path), EmptyRuntime)
    try:
        with pytest.raises(ValueError, match="already active"):
            start(other)
        service.close()
        job = start(other)
        assert wait_terminal(other, job["id"])["status"] == "completed"
    finally:
        other.close()


def test_queue_bound_per_owner_and_global(service):
    runtime = WaitingRuntime()
    service.runtime_factory = lambda: runtime
    first = start(service)
    assert runtime.started.wait(2)
    queued = start(service)
    with pytest.raises(ValueError, match="queue is full"):
        start(service)
    start(service, owner="bob")
    start(service, owner="bob")
    with pytest.raises(ValueError, match="queue is full"):
        start(service, owner="carol")
    assert service.cancel("alice", queued["id"])["status"] == "cancelled"
    replacement = start(service, owner="carol")
    assert replacement["status"] == "queued"
    service.cancel("alice", first["id"])


def test_timeout_cancels_runtime_and_returns_safe_error(service):
    runtime = WaitingRuntime()
    service.runtime_factory = lambda: runtime
    service.timeout = 0.05
    job = start(service)
    result = wait_terminal(service, job["id"])
    assert result["status"] == "failed"
    assert result["stage"] == "timeout"
    assert "time budget" in result["error"]
    assert runtime.cleaned.is_set()


def test_provider_error_does_not_leak_credentials(service):
    class BrokenRuntime:
        async def run(self, role, prompt):
            raise RuntimeError("https://provider.example/?token=SECRET_PRIVATE_VALUE")

    service.runtime_factory = BrokenRuntime
    job = start(service)
    result = wait_terminal(service, job["id"])
    assert result["status"] == "failed"
    assert "SECRET_PRIVATE_VALUE" not in str(result)
    assert "provider.example" not in str(service.store.get("alice", job["id"]))


def test_startup_marks_old_pending_jobs_interrupted(service):
    stale = service.store.create("alice", "Previous question", ["TCS.NS"], "quick")
    service.store.update("alice", stale["id"], status="running")
    new_job = start(service)
    assert wait_terminal(service, new_job["id"])["status"] == "completed"
    assert service.status("alice", stale["id"])["stage"] == "interrupted"
    assert service.status("alice", stale["id"])["status"] == "failed"


def test_close_finalizes_queued_jobs(service):
    runtime = WaitingRuntime()
    service.runtime_factory = lambda: runtime
    active = start(service)
    assert runtime.started.wait(2)
    queued = start(service)
    service.close()
    assert service.status("alice", active["id"])["status"] == "cancelled"
    assert service.status("alice", queued["id"])["status"] == "failed"
    assert service.status("alice", queued["id"])["stage"] == "interrupted"


def test_closed_service_rejects_new_jobs_and_close_is_idempotent(service):
    service.close()
    service.close()
    with pytest.raises(ValueError, match="service is closed"):
        start(service)


def test_worker_entering_during_close_does_not_start_runtime(service, monkeypatch):
    # Pause a submitted worker before it registers its event loop. Shutdown's
    # running-task snapshot cannot see it, so the closing guard must stop it.
    entered = threading.Event()
    release = threading.Event()
    closed = threading.Event()
    errors = []
    original_execute = service._execute
    runtime = WaitingRuntime()
    service.runtime_factory = lambda: runtime

    def delayed_execute(*args):
        entered.set()
        assert release.wait(3)
        return original_execute(*args)

    def close():
        try:
            service.close()
        except BaseException as exc:
            errors.append(exc)
        finally:
            closed.set()

    monkeypatch.setattr(service, "_execute", delayed_execute)
    job = start(service)
    assert entered.wait(2)
    closer = threading.Thread(target=close, daemon=True)
    closer.start()
    deadline = time.monotonic() + 2
    while not service._closing and time.monotonic() < deadline:
        time.sleep(0.005)
    assert service._closing
    release.set()
    assert closed.wait(2)
    closer.join()
    assert not errors
    assert not runtime.started.is_set()
    assert service.status("alice", job["id"])["stage"] == "interrupted"
