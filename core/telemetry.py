"""Fire-and-forget usage telemetry for MCP tool calls.

Every tool call produces an Event (tool_name, tool_category, session_id,
duration_ms, success, error) pushed onto a bounded in-process queue. A single
daemon thread drains the queue into Postgres (DATABASE_URL). Telemetry can
never block or break a tool call: all failures are swallowed, queue overflow
drops events, and with no DATABASE_URL the writer is a silent no-op.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import os
import queue
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger("mcp-quant-brain.telemetry")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS mcp_tool_events (
    id            BIGSERIAL PRIMARY KEY,
    ts            TIMESTAMPTZ      NOT NULL DEFAULT now(),
    tool_name     TEXT             NOT NULL,
    tool_category TEXT             NOT NULL,
    session_id    TEXT             NOT NULL,
    duration_ms   DOUBLE PRECISION NOT NULL,
    success       BOOLEAN          NOT NULL,
    error         TEXT
);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_events_ts       ON mcp_tool_events (ts);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_events_category ON mcp_tool_events (tool_category);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_events_session  ON mcp_tool_events (session_id);
"""

_INSERT_SQL = (
    "INSERT INTO mcp_tool_events "
    "(tool_name, tool_category, session_id, duration_ms, success, error) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)

_SUMMARY_SQL = """
SELECT
  count(*)                                                    AS total_requests,
  count(DISTINCT session_id)                                  AS unique_sessions,
  count(*) FILTER (WHERE tool_category = 'backtest')          AS backtests,
  count(*) FILTER (WHERE tool_category = 'optimization')      AS optimizations,
  avg(CASE WHEN success THEN 1.0 ELSE 0.0 END)                AS success_rate,
  percentile_cont(0.5)  WITHIN GROUP (ORDER BY duration_ms)   AS p50_latency,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms)   AS p95_latency
FROM mcp_tool_events
"""


@dataclass
class Event:
    tool_name: str
    tool_category: str
    session_id: str
    duration_ms: float
    success: bool
    error: str | None


class TelemetryWriter:
    """Background writer: bounded queue drained by one daemon thread."""

    def __init__(self, dsn: str | None, start_thread: bool = True):
        self.dsn = dsn
        self.enabled = bool(dsn)
        self.queue: queue.Queue[Event] = queue.Queue(maxsize=10000)
        self.dropped = 0
        self._conn = None
        if self.enabled and start_thread:
            thread = threading.Thread(target=self._run, name="telemetry-writer", daemon=True)
            thread.start()

    def submit(self, event: Event) -> None:
        if not self.enabled:
            return
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            self.dropped += 1
            if self.dropped % 1000 == 1:
                logger.warning("telemetry queue full; dropped %d events so far", self.dropped)

    # -- daemon thread side -------------------------------------------------

    def _connect(self):
        import psycopg2

        conn = psycopg2.connect(self.dsn)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
        return conn

    def _run(self) -> None:
        backoff = 1.0
        while True:
            event = self.queue.get()
            while True:
                try:
                    if self._conn is None or self._conn.closed:
                        self._conn = self._connect()
                    with self._conn.cursor() as cur:
                        cur.execute(
                            _INSERT_SQL,
                            (
                                event.tool_name,
                                event.tool_category,
                                event.session_id,
                                event.duration_ms,
                                event.success,
                                event.error,
                            ),
                        )
                    backoff = 1.0
                    break
                except Exception as exc:
                    logger.warning("telemetry insert failed (%s); retrying in %.0fs", exc, backoff)
                    try:
                        if self._conn is not None:
                            self._conn.close()
                    except Exception:
                        pass
                    self._conn = None
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60.0)


_writer: TelemetryWriter | None = None
_writer_lock = threading.Lock()


def _get_writer() -> TelemetryWriter:
    global _writer
    if _writer is None:
        with _writer_lock:
            if _writer is None:
                dsn = os.getenv("DATABASE_URL")
                _writer = TelemetryWriter(dsn)
                if not dsn:
                    logger.info("DATABASE_URL not set; telemetry disabled")
    return _writer


def record(event: Event) -> None:
    """Queue one event. Never raises."""
    try:
        _get_writer().submit(event)
    except Exception:
        pass


def derive_session_id(get_context) -> str:
    """Best-effort session id: mcp-session-id header, else client fingerprint.

    The server runs stateless HTTP (no server-assigned session ids), so the
    fingerprint of client IP + user agent is a stable proxy for unique clients.
    Never raises.
    """
    try:
        if get_context is None:
            return "unknown"
        ctx = get_context()
        request = ctx.request_context.request
        if request is None:
            return "unknown"
        header = request.headers.get("mcp-session-id")
        if header:
            return str(header)[:128]
        host = getattr(getattr(request, "client", None), "host", "") or ""
        user_agent = request.headers.get("user-agent", "") or ""
        if not host and not user_agent:
            return "unknown"
        digest = hashlib.sha1(f"{host}|{user_agent}".encode()).hexdigest()[:16]
        return f"fp_{digest}"
    except Exception:
        return "unknown"


def instrument(fn, category: str, get_context=None):
    """Wrap a tool function so every call emits one telemetry event.

    success is False when the call raises OR returns a dict containing an
    "error" key (the codebase's soft-error convention). Exceptions re-raise.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        success = True
        error: str | None = None
        try:
            result = fn(*args, **kwargs)
            if isinstance(result, dict) and "error" in result:
                success = False
                error = str(result["error"])[:500]
            return result
        except Exception as exc:
            success = False
            error = str(exc)[:500]
            raise
        finally:
            try:
                record(
                    Event(
                        tool_name=fn.__name__,
                        tool_category=category,
                        session_id=derive_session_id(get_context),
                        duration_ms=(time.perf_counter() - start) * 1000.0,
                        success=success,
                        error=error,
                    )
                )
            except Exception:
                pass

    return wrapper


def fetch_summary() -> dict | None:
    """Run the aggregate metrics query. Returns None when DATABASE_URL is unset.

    Called from the /metrics/summary route via asyncio.to_thread; uses its own
    short-lived connection so it never contends with the writer thread.
    """
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return None

    import psycopg2

    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
            conn.commit()
            cur.execute(_SUMMARY_SQL)
            row = cur.fetchone()
    finally:
        conn.close()

    total, sessions, backtests, optimizations, rate, p50, p95 = row
    return {
        "total_requests": int(total or 0),
        "unique_sessions": int(sessions or 0),
        "backtests": int(backtests or 0),
        "optimizations": int(optimizations or 0),
        "success_rate": round(float(rate), 4) if rate is not None else None,
        "p50_latency": round(float(p50), 1) if p50 is not None else None,
        "p95_latency": round(float(p95), 1) if p95 is not None else None,
    }
