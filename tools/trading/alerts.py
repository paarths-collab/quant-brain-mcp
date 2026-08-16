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
from datetime import datetime, timezone

from core.telemetry import _normalize_dsn
from tools.trading.quotes import get_quotes

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS price_alerts (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ticker          TEXT NOT NULL,
    direction       TEXT NOT NULL CHECK (direction IN ('above', 'below')),
    level           DOUBLE PRECISION NOT NULL,
    note            TEXT,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    triggered_at    TIMESTAMPTZ,
    triggered_price DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_price_alerts_active ON price_alerts (active);
"""


def _db_available() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def _connect():
    import psycopg2

    conn = psycopg2.connect(_normalize_dsn(os.getenv("DATABASE_URL")))
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(_SCHEMA_SQL)
    return conn


def _insert_alert(ticker: str, direction: str, level: float, note: str | None) -> int:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO price_alerts (ticker, direction, level, note) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (ticker, direction, level, note),
            )
            return int(cur.fetchone()[0])
    finally:
        conn.close()


def _fetch_alerts(active_only: bool = True) -> list[dict]:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            query = (
                "SELECT id, ticker, direction, level, note, active, triggered_at, triggered_price "
                "FROM price_alerts"
            )
            if active_only:
                query += " WHERE active"
            query += " ORDER BY id"
            cur.execute(query)
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


def _deactivate_alert(alert_id: int, triggered_price: float | None = None) -> bool:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            if triggered_price is not None:
                cur.execute(
                    "UPDATE price_alerts SET active = FALSE, triggered_at = now(), "
                    "triggered_price = %s WHERE id = %s AND active",
                    (triggered_price, alert_id),
                )
            else:
                cur.execute(
                    "UPDATE price_alerts SET active = FALSE WHERE id = %s AND active",
                    (alert_id,),
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
) -> dict:
    """Set, list, delete, or check price alerts. See the MCP tool docstring."""
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
            return _do_set(ticker, level, direction, note)
        if action == "list":
            return {"alerts": _fetch_alerts(active_only=True)}
        if action == "delete":
            return _do_delete(alert_id)
        return _do_check()
    except Exception as exc:
        return {"error": f"Alert storage error: {exc}"}


def _do_set(ticker, level, direction, note) -> dict:
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
    if level <= 0:
        return {"error": "Price level must be positive."}

    new_id = _insert_alert(symbol, direction, level, note)
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


def _do_delete(alert_id) -> dict:
    try:
        alert_id = int(alert_id)
    except (TypeError, ValueError):
        return {"error": "Provide a numeric alert_id (see action='list')."}
    if _deactivate_alert(alert_id):
        return {"deleted": True, "alert_id": alert_id}
    return {"error": f"No active alert with id {alert_id}."}


def _do_check() -> dict:
    active = _fetch_alerts(active_only=True)
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
    still_watching = 0
    for alert in active:
        quote = quotes.get(alert["ticker"], {})
        price = quote.get("last_price")
        if price is None:
            still_watching += 1  # unfetchable now; keep watching, never drop silently
            continue

        fired = (alert["direction"] == "below" and price <= alert["level"]) or (
            alert["direction"] == "above" and price >= alert["level"]
        )
        if fired:
            _deactivate_alert(alert["id"], triggered_price=price)
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

    return {
        "triggered": triggered,
        "still_watching": still_watching,
        "as_of": quote_result.get("as_of"),
    }
