"""Durable, owner-scoped research jobs. No filesystem activity occurs on import."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TERMINAL = frozenset({"completed", "failed", "cancelled"})
_STATUSES = _TERMINAL | {"queued", "running"}
_UNSET = object()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchStore:
    """Each operation uses its own connection; transactions serialize mutations."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.environ.get(
            "QUANT_RESEARCH_DB", "~/.local/share/quant-brain/research.sqlite3"
        )).expanduser()

    @contextmanager
    def _connection(self):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Create private database files without changing existing directory permissions.
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        connection = sqlite3.connect(str(self.path), timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS research_jobs (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    question TEXT NOT NULL, tickers TEXT NOT NULL,
                    depth TEXT NOT NULL, status TEXT NOT NULL,
                    stage TEXT NOT NULL, created TEXT NOT NULL,
                    updated TEXT NOT NULL, report TEXT, error TEXT
                );
                CREATE TABLE IF NOT EXISTS research_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES research_jobs(id),
                    role TEXT NOT NULL, payload TEXT NOT NULL,
                    created TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS research_event_job
                    ON research_events(job_id, id);
            """)
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _read(connection, owner: str, job_id: str) -> dict | None:
        row = connection.execute(
            "SELECT * FROM research_jobs WHERE owner=? AND id=?", (owner, job_id)
        ).fetchone()
        if row is None:
            return None
        job = dict(row)
        job.pop("owner")
        job["tickers"] = json.loads(job["tickers"])
        job["report"] = json.loads(job["report"]) if job["report"] is not None else None
        job["events"] = [
            {**dict(event), "payload": json.loads(event["payload"])}
            for event in connection.execute(
                "SELECT id, role, payload, created FROM research_events WHERE job_id=? ORDER BY id",
                (job_id,),
            ).fetchall()
        ]
        return job

    def create(self, owner: str, question: str, tickers: list[str], depth: str) -> dict:
        if not owner:
            raise ValueError("Research jobs require an owner")
        job_id, now = str(uuid.uuid4()), _now()
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO research_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, owner, question, json.dumps(tickers), depth, "queued", "queued", now, now, None, None),
            )
            return self._read(connection, owner, job_id)

    def get(self, owner: str, job_id: str) -> dict | None:
        with self._connection() as connection:
            return self._read(connection, owner, job_id)

    def update(self, owner: str, job_id: str, *, status: str | None = None,
               stage: str | None = None, report: Any = _UNSET,
               error: str | None | object = _UNSET) -> dict | None:
        if status is not None and status not in _STATUSES:
            raise ValueError("Invalid research job status")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            job = self._read(connection, owner, job_id)
            if job is None or job["status"] in _TERMINAL:
                return job
            changes = {"updated": _now()}
            if status is not None:
                if job["status"] == "running" and status == "queued":
                    raise ValueError("Running research cannot return to queued")
                changes["status"] = status
            if stage is not None:
                changes["stage"] = stage
            if report is not _UNSET:
                changes["report"] = json.dumps(report)
            if error is not _UNSET:
                changes["error"] = error
            columns = ", ".join(f"{column}=?" for column in changes)
            connection.execute(
                f"UPDATE research_jobs SET {columns} WHERE owner=? AND id=?",
                (*changes.values(), owner, job_id),
            )
            return self._read(connection, owner, job_id)

    def event(self, owner: str, job_id: str, role: str, payload: Any) -> dict | None:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            job = self._read(connection, owner, job_id)
            if job is None or job["status"] in _TERMINAL:
                return job
            now = _now()
            connection.execute(
                "INSERT INTO research_events(job_id, role, payload, created) VALUES (?, ?, ?, ?)",
                (job_id, role, json.dumps(payload), now),
            )
            connection.execute(
                "UPDATE research_jobs SET updated=? WHERE owner=? AND id=?",
                (now, owner, job_id),
            )
            return self._read(connection, owner, job_id)

    def cancel(self, owner: str, job_id: str) -> dict | None:
        return self.update(owner, job_id, status="cancelled", stage="cancelled")

    def active_count(self, owner: str | None = None) -> int:
        """Count pending work; caller must serialize admission with job creation."""
        with self._connection() as connection:
            sql = "SELECT COUNT(*) FROM research_jobs WHERE status IN ('queued', 'running')"
            parameters = ()
            if owner is not None:
                sql += " AND owner=?"
                parameters = (owner,)
            return connection.execute(sql, parameters).fetchone()[0]

    def recover_interrupted(self) -> int:
        """Call only at startup while holding the application's exclusive worker lock."""
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE research_jobs SET status='failed', stage='interrupted', error=?, updated=? "
                "WHERE status IN ('queued', 'running')",
                ("Research interrupted by application restart; start a new job.", _now()),
            )
            return cursor.rowcount
