"""Research job lifecycle against fake model and market-data providers only.

Nothing here makes a paid or live call: the model is ScriptedRuntime, the
market-data lookup is FakeMarketData, and `no_live_network` fails any test that
tries to reach the network.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from core.research_service import ResearchService
from core.research_store import ResearchStore
from tests.research_fakes import FakeMarketData, ScriptedRuntime

pytestmark = pytest.mark.usefixtures("no_live_network")

REPO_ROOT = Path(__file__).resolve().parent.parent
# Generous: every wait returns the moment its event fires, so these only matter on a starved CI box.
TERMINAL = {"completed", "failed", "cancelled"}


def make_service(tmp_path, runtime_factory, market=None, **kwargs):
    return ResearchService(ResearchStore(tmp_path / "jobs.sqlite3"), runtime_factory,
                           instrument_resolver=market or FakeMarketData(), timeout=60, **kwargs)


@pytest.fixture
def services():
    created = []
    yield created
    for service in created:
        service.close()


def open_service(services, tmp_path, runtime_factory, **kwargs):
    service = make_service(tmp_path, runtime_factory, **kwargs)
    services.append(service)
    return service


def start(service, owner="alice", tickers=("TCS",), depth="quick"):
    return service.start(owner, "Review this company", list(tickers), depth)


def wait_terminal(service, job_id, owner="alice"):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        status = service.status(owner, job_id)
        if status.get("status") in TERMINAL:
            return status
        time.sleep(0.01)
    pytest.fail("job did not reach a terminal state")


def event_pairs(service, job_id, owner="alice"):
    return [(e["role"], e["payload"]["status"]) for e in service.store.get(owner, job_id)["events"]]


# --- success -----------------------------------------------------------------

def test_success_persists_report_and_every_stage(services, tmp_path):
    runtime = ScriptedRuntime()
    service = open_service(services, tmp_path, lambda: runtime)
    job = start(service)
    assert job["status"] == "queued" and job["tickers"] == ["TCS.NS"]

    assert wait_terminal(service, job["id"])["status"] == "completed"
    result = service.report("alice", job["id"])
    report = result["report"]
    assert report["tickers"] == ["TCS.NS"]
    assert report["verified_claim_ids"] == ["company_c1"]
    assert report["invocation_count"] == len(runtime.roles) == 4
    assert {role for role, _ in event_pairs(service, job["id"])} == {"company", "quant", "auditor", "synthesizer"}
    assert all(state in {"running", "completed"} for _, state in event_pairs(service, job["id"]))
    # The same report is what a fresh reader of the database sees.
    assert ResearchStore(service.store.path).get("alice", job["id"])["report"] == report
    # The unfetchable example.com source is reported as such, not hidden.
    assert report["source_coverage"]["total"] == 1 and report["source_coverage"]["retrieved"] == 0


# --- provider failure part-way -------------------------------------------------

def test_provider_failure_midway_fails_job_without_a_report_or_leak(services, tmp_path):
    runtimes = iter([ScriptedRuntime(fail_at="auditor"), ScriptedRuntime()])
    service = open_service(services, tmp_path, lambda: next(runtimes))
    broken = start(service)

    result = wait_terminal(service, broken["id"])
    assert result["status"] == "failed" and result["stage"] == "failed"
    assert "SECRET_PRIVATE_VALUE" not in str(result) and "provider.example" not in str(result)
    assert service.report("alice", broken["id"])["report"] is None
    stored = service.store.get("alice", broken["id"])
    assert stored["report"] is None
    # Progress made before the failure is kept; the failing stage never completed.
    pairs = event_pairs(service, broken["id"])
    assert ("company", "completed") in pairs and ("quant", "completed") in pairs
    assert ("auditor", "completed") not in pairs and ("synthesizer", "running") not in pairs
    assert "SECRET_PRIVATE_VALUE" not in str(stored)

    # The worker is not wedged: the next job runs to completion.
    healthy = start(service)
    assert wait_terminal(service, healthy["id"])["status"] == "completed"
    assert service.store.active_count() == 0


# --- cancellation while running -------------------------------------------------

def test_cancel_while_running_stops_work_and_never_produces_a_report(services, tmp_path):
    runtime = ScriptedRuntime(block_at="auditor")
    service = open_service(services, tmp_path, lambda: runtime)
    job = start(service)
    assert runtime.started.wait(30)
    assert service.status("alice", job["id"])["status"] == "running"

    assert service.cancel("alice", job["id"])["status"] == "cancelled"
    assert runtime.cleaned.wait(30)          # the in-flight model call was actually cancelled
    time.sleep(0.1)                         # give a (wrongly) surviving worker time to overwrite state
    final = service.status("alice", job["id"])
    assert final["status"] == "cancelled" and final["stage"] == "cancelled"
    assert service.report("alice", job["id"])["report"] is None
    pairs = event_pairs(service, job["id"])
    assert ("auditor", "completed") not in pairs and not any(role == "synthesizer" for role, _ in pairs)
    assert "synthesizer" not in runtime.roles

    # Cancelling again is harmless, and the freed worker takes the next job.
    assert service.cancel("alice", job["id"])["status"] == "cancelled"
    service.runtime_factory = ScriptedRuntime
    assert wait_terminal(service, start(service)["id"])["status"] == "completed"


# --- restart with a job in progress ---------------------------------------------

CRASH_SCRIPT = """
import os, sys
from core.research_service import ResearchService
from core.research_store import ResearchStore
from tests.research_fakes import FakeMarketData, ScriptedRuntime

runtime = ScriptedRuntime(block_at="auditor")
service = ResearchService(ResearchStore(sys.argv[1]), lambda: runtime, instrument_resolver=FakeMarketData())
job = service.start("alice", "Review this company", ["TCS"], "quick")
assert runtime.started.wait(30)
print(job["id"], flush=True)
os._exit(0)  # hard stop: no close(), no cleanup, job still 'running'
"""


def crash_with_job_in_progress(db_path):
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    out = subprocess.run([sys.executable, "-c", CRASH_SCRIPT, str(db_path)], cwd=REPO_ROOT, env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip().splitlines()[-1]


def test_restart_after_hard_stop_marks_orphaned_job_failed_even_before_new_work(services, tmp_path):
    db = tmp_path / "jobs.sqlite3"
    orphan = crash_with_job_in_progress(db)
    assert ResearchStore(db).get("alice", orphan)["status"] == "running"   # what the dead process left behind

    service = open_service(services, tmp_path, ScriptedRuntime)
    # A client polling after the restart must not be told a dead job is still running.
    status = service.status("alice", orphan)
    assert (status["status"], status["stage"]) == ("failed", "interrupted")
    assert "restart" in status["error"]
    assert service.report("alice", orphan)["report"] is None

    fresh = start(service)
    assert wait_terminal(service, fresh["id"])["status"] == "completed"
    assert service.status("alice", orphan)["status"] == "failed"   # and it is not resurrected


def test_graceful_shutdown_then_restart_keeps_history_consistent(services, tmp_path):
    runtime = ScriptedRuntime(block_at="auditor")
    first = open_service(services, tmp_path, lambda: runtime)
    running = start(first)
    assert runtime.started.wait(30)
    queued = start(first)
    first.close()
    assert first.status("alice", running["id"])["status"] == "cancelled"
    assert first.status("alice", queued["id"])["stage"] == "interrupted"

    second = open_service(services, tmp_path, ScriptedRuntime)
    assert second.status("alice", running["id"])["status"] == "cancelled"
    assert second.status("alice", queued["id"])["status"] == "failed"
    assert wait_terminal(second, start(second)["id"])["status"] == "completed"


# --- owner scoping ----------------------------------------------------------------

def test_owner_cannot_read_cancel_or_affect_another_owners_job(services, tmp_path):
    runtime = ScriptedRuntime(block_at="auditor")
    service = open_service(services, tmp_path, lambda: runtime)
    bobs = start(service, owner="bob")
    assert runtime.started.wait(30)

    denied = {"error": "Research job not found"}
    for method in (service.status, service.report, service.cancel):
        assert method("alice", bobs["id"]) == denied
    for impostor in ("", "%", "bob ", "BOB", "alice' OR '1'='1"):
        assert service.status(impostor, bobs["id"]) == denied
    assert service.store.get("alice", bobs["id"]) is None

    # alice's attempted cancel changed nothing for bob.
    assert service.status("bob", bobs["id"])["status"] == "running"
    assert not runtime.cleaned.is_set()
    assert service.cancel("bob", bobs["id"])["status"] == "cancelled"


def test_completed_report_is_private_and_each_owner_sees_only_their_own(services, tmp_path):
    service = open_service(services, tmp_path, ScriptedRuntime)
    alice = start(service, owner="alice", tickers=("TCS",))
    bob = start(service, owner="bob", tickers=("INFY",))
    wait_terminal(service, alice["id"], "alice")
    wait_terminal(service, bob["id"], "bob")

    assert service.report("alice", alice["id"])["report"]["tickers"] == ["TCS.NS"]
    assert service.report("bob", bob["id"])["report"]["tickers"] == ["INFY.NS"]
    assert service.report("alice", bob["id"]) == {"error": "Research job not found"}
    assert service.report("bob", alice["id"]) == {"error": "Research job not found"}
    assert "INFY" not in str(service.store.get("alice", alice["id"]))


def test_per_owner_queue_limit_does_not_block_other_owners(services, tmp_path):
    runtime = ScriptedRuntime(block_at="auditor")
    service = open_service(services, tmp_path, lambda: runtime)
    start(service, owner="alice")
    assert runtime.started.wait(30)
    start(service, owner="alice")
    with pytest.raises(ValueError, match="queue is full"):
        start(service, owner="alice")
    assert start(service, owner="bob")["status"] == "queued"
