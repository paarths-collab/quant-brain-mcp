"""Persistent price alerts: set a level once, poll cheaply, fire once.

Architecture note: MCP is request/response -- a server cannot push a message
into Claude. Alerts therefore live server-side in Postgres (surviving Render
restarts) and a scheduled Claude task polls `check` on a cadence, speaking up
only when something fired. The server is the memory; the scheduled task is
the messenger.

Alerts are ONE-SHOT: once triggered they deactivate, so a level that keeps
being crossed does not spam every poll.
"""

from __future__ import annotations

import os
import math
import logging
import threading
from datetime import datetime, timezone

from core.telemetry import _normalize_dsn
from tools.trading.quotes import get_quotes

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS price_alerts (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    owner_id        TEXT,
    ticker          TEXT NOT NULL,
    direction       TEXT NOT NULL CHECK (direction IN ('above', 'below')),
    level           DOUBLE PRECISION NOT NULL,
    note            TEXT,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    triggered_at    TIMESTAMPTZ,
    triggered_price DOUBLE PRECISION
);
ALTER TABLE price_alerts ADD COLUMN IF NOT EXISTS owner_id TEXT;
CREATE INDEX IF NOT EXISTS idx_price_alerts_owner_active ON price_alerts (owner_id, active);
"""


# Rows created before alerts were owner-scoped have owner_id NULL and are
# invisible to every owner. Setting this env var assigns them to that owner
# once at schema initialization; unset, they are left untouched.
_LEGACY_OWNER_ENV = "PRICE_ALERTS_LEGACY_OWNER"

# DSNs whose schema has been initialized by this process.
_schema_ready: set[str] = set()
_schema_lock = threading.Lock()


def _db_available() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def _ensure_schema(conn, dsn: str) -> None:
    """Run DDL once per process and database.

    ALTER TABLE takes an ACCESS EXCLUSIVE lock even when the column already
    exists, so running it on every set/list/check serialized all alert traffic.
    """
    if dsn in _schema_ready:
        return
    with _schema_lock:
        if dsn in _schema_ready:
            return
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
            legacy_owner = (os.getenv(_LEGACY_OWNER_ENV) or "").strip()
            if legacy_owner:
                cur.execute("UPDATE price_alerts SET owner_id = %s WHERE owner_id IS NULL", (legacy_owner,))
        _schema_ready.add(dsn)


def _connect():
    import psycopg2

    dsn = _normalize_dsn(os.getenv("DATABASE_URL"))
    conn = psycopg2.connect(dsn, connect_timeout=10)
    conn.autocommit = True
    try:
        _ensure_schema(conn, dsn)
    except Exception:
        conn.close()
        raise
    return conn


def _insert_alert(owner_id: str, ticker: str, direction: str, level: float, note: str | None) -> int:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO price_alerts (owner_id, ticker, direction, level, note) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (owner_id, ticker, direction, level, note),
            )
            return int(cur.fetchone()[0])
    finally:
        conn.close()


def _fetch_alerts(owner_id: str, active_only: bool = True) -> list[dict]:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            query = (
                "SELECT id, ticker, direction, level, note, active, triggered_at, triggered_price "
                "FROM price_alerts WHERE owner_id = %s"
            )
            if active_only:
                query += " AND active"
            query += " ORDER BY id"
            cur.execute(query, (owner_id,))
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0],
            "ticker": r[1],
            "direction": r[2],
            "level": r[3],
            "note": r[4],
            "active": r[5],
            "triggered_at": r[6].isoformat() if r[6] else None,
            "triggered_price": r[7],
        }
        for r in rows
    ]


def _deactivate_alert(owner_id: str, alert_id: int, triggered_price: float | None = None) -> bool:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            if triggered_price is not None:
                cur.execute(
                    "UPDATE price_alerts SET active = FALSE, triggered_at = now(), "
                    "triggered_price = %s WHERE id = %s AND owner_id = %s AND active",
                    (triggered_price, alert_id, owner_id),
                )
            else:
                cur.execute(
                    "UPDATE price_alerts SET active = FALSE WHERE id = %s AND owner_id = %s AND active",
                    (alert_id, owner_id),
                )
            return cur.rowcount > 0
    finally:
        conn.close()


def manage_alert(
    action: str,
    ticker: str | None = None,
    level: float | None = None,
    direction: str | None = None,
    alert_id: int | None = None,
    note: str | None = None,
    *,
    owner_id: str | None = None,
) -> dict:
    """Set, list, delete, or check price alerts. See the MCP tool docstring."""
    if not isinstance(owner_id, str) or not owner_id.strip():
        return {"error": "Authenticated identity is required for price alerts."}
    action = str(action).strip().lower()
    if action not in {"set", "list", "delete", "check"}:
        return {"error": f"Unknown action '{action}'. Use 'set', 'list', 'delete', or 'check'."}

    if not _db_available():
        return {
            "error": (
                "Price alerts require persistent storage but DATABASE_URL is not "
                "configured on the server."
            )
        }

    try:
        if action == "set":
            return _do_set(owner_id, ticker, level, direction, note)
        if action == "list":
            return {"alerts": _fetch_alerts(owner_id, active_only=True)}
        if action == "delete":
            return _do_delete(owner_id, alert_id)
        return _do_check(owner_id)
    except Exception:
        logging.getLogger(__name__).warning("Alert storage operation failed")
        return {"error": "Alert storage is temporarily unavailable. Please retry."}


def _do_set(owner_id, ticker, level, direction, note) -> dict:
    symbol = str(ticker or "").strip().upper()
    if not symbol:
        return {"error": "Provide a ticker symbol."}
    direction = str(direction or "").strip().lower()
    if direction not in {"above", "below"}:
        return {"error": "direction must be 'above' or 'below'."}
    try:
        level = float(level)
    except (TypeError, ValueError):
        return {"error": "Provide a numeric price level."}
    if not math.isfinite(level) or level <= 0:
        return {"error": "Price level must be finite and positive."}

    new_id = _insert_alert(owner_id, symbol, direction, level, note)
    return {
        "alert_id": new_id,
        "ticker": symbol,
        "direction": direction,
        "level": level,
        "status": (
            f"Watching {symbol}: will fire once when price moves {direction} {level}. "
            "Alerts are one-shot and require a scheduled task polling action='check'."
        ),
    }


def _do_delete(owner_id, alert_id) -> dict:
    try:
        if isinstance(alert_id, bool) or str(alert_id).strip() != str(int(alert_id)) or int(alert_id) <= 0:
            raise ValueError("Invalid alert id")
        alert_id = int(alert_id)
    except (TypeError, ValueError, OverflowError):
        return {"error": "Provide a numeric alert_id (see action='list')."}
    if _deactivate_alert(owner_id, alert_id):
        return {"deleted": True, "alert_id": alert_id}
    return {"error": f"No active alert with id {alert_id}."}


def _do_check(owner_id) -> dict:
    active = _fetch_alerts(owner_id, active_only=True)
    if not active:
        return {
            "triggered": [],
            "still_watching": 0,
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    tickers = sorted({a["ticker"] for a in active})
    quote_result = get_quotes(tickers)
    quotes = quote_result.get("quotes", {})

    triggered = []
    unpriced = []
    still_watching = 0
    for alert in active:
        quote = quotes.get(alert["ticker"], {})
        price = quote.get("last_price")
        try:
            price = float(price)
        except (TypeError, ValueError):
            price = float("nan")
        if not math.isfinite(price) or price <= 0:
            still_watching += 1  # unfetchable now; keep watching, never drop silently
            unpriced.append({
                "alert_id": alert["id"],
                "ticker": alert["ticker"],
                "reason": quote.get("error") or "No valid price returned",
            })
            continue

        fired = (alert["direction"] == "below" and price <= alert["level"]) or (
            alert["direction"] == "above" and price >= alert["level"]
        )
        if fired:
            if not _deactivate_alert(owner_id, alert["id"], triggered_price=price):
                continue  # another poll or deletion claimed this alert first
            triggered.append(
                {
                    "alert_id": alert["id"],
                    "ticker": alert["ticker"],
                    "direction": alert["direction"],
                    "level": alert["level"],
                    "current_price": price,
                    "note": alert["note"],
                }
            )
        else:
            still_watching += 1

    result = {
        "triggered": triggered,
        "still_watching": still_watching,
        "unpriced": unpriced,
        "as_of": quote_result.get("as_of"),
    }
    if unpriced:
        result["warning"] = (
            f"{len(unpriced)} alert(s) could not be priced and were not evaluated; "
            "check the symbols (e.g. add .NS for NSE) or retry later."
        )
    return result
