"""Real SQL regression tests; set TEST_DATABASE_URL to a disposable Postgres DB.

Each test owns a randomly named schema and removes it afterward.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from tools.trading import alerts


@pytest.fixture
def database(monkeypatch):
    dsn = os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL not configured")
    psycopg2 = pytest.importorskip("psycopg2")
    from psycopg2.extensions import make_dsn
    from psycopg2 import sql

    schema = "alerts_test_" + uuid4().hex
    admin = psycopg2.connect(dsn)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    scoped_dsn = make_dsn(dsn, options=f"-c search_path={schema}")
    monkeypatch.setenv("DATABASE_URL", scoped_dsn)
    monkeypatch.setattr(alerts, "_normalize_dsn", lambda value: value)
    try:
        yield scoped_dsn
    finally:
        with admin.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        admin.close()


def test_real_sql_owner_isolation_and_legacy_migration(database):
    import psycopg2

    conn = psycopg2.connect(database)
    conn.autocommit = True
    # An existing deployment's table has no owner column.
    old_schema = alerts._SCHEMA_SQL.split("ALTER TABLE")[0].replace("    owner_id        TEXT,\n", "")
    with conn.cursor() as cur:
        cur.execute(old_schema)
        cur.execute("INSERT INTO price_alerts(ticker,direction,level) VALUES ('LEGACY','above',10)")
    conn.close()
    assert alerts._fetch_alerts("alice") == []
    alert_id = alerts._insert_alert("alice", "AAPL", "above", 100, "private")
    assert len(alerts._fetch_alerts("alice")) == 1
    assert alerts._fetch_alerts("bob") == []
    assert not alerts._deactivate_alert("bob", alert_id)
    assert alerts._deactivate_alert("alice", alert_id)
    assert alerts._fetch_alerts("alice") == []


def test_real_sql_concurrent_trigger_claim_has_one_winner(database):
    alert_id = alerts._insert_alert("alice", "AAPL", "above", 100, None)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: alerts._deactivate_alert("alice", alert_id, 110), range(4)))
    assert results.count(True) == 1
    rows = alerts._fetch_alerts("alice", active_only=False)
    assert rows[0]["triggered_price"] == 110
    assert rows[0]["triggered_at"]
