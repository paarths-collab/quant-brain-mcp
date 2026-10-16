from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from core.research_store import ResearchStore


@pytest.fixture
def store(tmp_path):
    return ResearchStore(tmp_path / "research.sqlite3")


def create(store, owner="alice"):
    return store.create(owner, "Compare company fundamentals", ["EXAMPLE.NS"], "standard")


def test_lazy_initialization(tmp_path):
    path = tmp_path / "nested" / "jobs.sqlite3"
    ResearchStore(path)
    assert not path.exists()


def test_persistence_and_owner_isolation(store):
    job = create(store)
    store.event("alice", job["id"], "analyst", {"finding": "example"})
    store.update("alice", job["id"], status="completed", report={"summary": "done"})
    restored = ResearchStore(store.path).get("alice", job["id"])
    assert restored["report"] == {"summary": "done"}
    assert restored["events"][0]["payload"] == {"finding": "example"}
    assert "owner" not in restored
    assert store.get("bob", job["id"]) is None
    assert store.update("bob", job["id"], status="failed") is None
    assert store.cancel("bob", job["id"]) is None
    assert store.event("bob", job["id"], "reviewer", {}) is None


def test_cancel_blocks_late_worker_results(store):
    job = create(store)
    store.update("alice", job["id"], status="running")
    store.cancel("alice", job["id"])
    store.update("alice", job["id"], status="completed", report={"late": True})
    store.event("alice", job["id"], "late", {})
    result = store.get("alice", job["id"])
    assert result["status"] == "cancelled"
    assert result["report"] is None
    assert result["events"] == []


def test_cancel_update_race_has_consistent_terminal_result(store):
    job = create(store)
    barrier = Barrier(2)

    def cancel():
        barrier.wait()
        return store.cancel("alice", job["id"])

    def finish():
        barrier.wait()
        return store.update("alice", job["id"], status="completed", report={"done": True})

    with ThreadPoolExecutor(2) as pool:
        tasks = [pool.submit(cancel), pool.submit(finish)]
        for task in tasks:
            task.result()
    result = store.get("alice", job["id"])
    assert result["status"] in {"completed", "cancelled"}
    assert result["report"] == ({"done": True} if result["status"] == "completed" else None)


def test_restart_recovery_preserves_terminal_jobs(store):
    queued = create(store)
    running = create(store)
    complete = create(store)
    store.update("alice", running["id"], status="running")
    store.update("alice", complete["id"], status="completed", report={})
    assert store.recover_interrupted() == 2
    for job in (queued, running):
        assert store.get("alice", job["id"])["status"] == "failed"
    assert store.get("alice", complete["id"])["status"] == "completed"
    assert store.recover_interrupted() == 0


def test_invalid_transitions(store):
    job = create(store)
    with pytest.raises(ValueError):
        store.update("alice", job["id"], status="unknown")
    store.update("alice", job["id"], status="running")
    with pytest.raises(ValueError):
        store.update("alice", job["id"], status="queued")
    with pytest.raises(ValueError):
        create(store, owner="")


def test_active_count_and_private_permissions(store):
    import stat

    first = create(store)
    create(store, "bob")
    assert store.active_count() == 2
    assert store.active_count("alice") == 1
    assert store.active_count("other") == 0
    store.cancel("alice", first["id"])
    assert store.active_count() == 1
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
