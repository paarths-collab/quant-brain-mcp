"""Tests for the price_alert tool (set / list / delete / check).

Storage is a thin SQL layer (Supabase Postgres via DATABASE_URL) mocked out
here; these tests pin the LOGIC: validation, trigger comparison, one-shot
semantics, and graceful degradation when no database is configured.
"""

from unittest.mock import patch

import pytest

from tools.trading import alerts


def manage(*args, **kwargs):
    kwargs.setdefault("owner_id", "test-user")
    return alerts.manage_alert(*args, **kwargs)


@pytest.fixture(autouse=True)
def _fake_store(monkeypatch):
    """Replace the SQL layer with an in-memory store."""
    rows: list[dict] = []
    counter = {"id": 0}

    def fake_insert(owner_id, ticker, direction, level, note):
        counter["id"] += 1
        row = {
            "id": counter["id"],
            "owner_id": owner_id,
            "ticker": ticker,
            "direction": direction,
            "level": level,
            "note": note,
            "active": True,
            "triggered_at": None,
            "triggered_price": None,
        }
        rows.append(row)
        return counter["id"]

    def fake_fetch(owner_id, active_only=True):
        return [dict(r) for r in rows if r["owner_id"] == owner_id and (r["active"] or not active_only)]

    def fake_deactivate(owner_id, alert_id, triggered_price=None):
        for r in rows:
            if r["id"] == alert_id and r["owner_id"] == owner_id and r["active"]:
                r["active"] = False
                if triggered_price is not None:
                    r["triggered_at"] = "2026-08-16T12:00:00Z"
                    r["triggered_price"] = triggered_price
                return True
        return False

    monkeypatch.setattr(alerts, "_insert_alert", fake_insert)
    monkeypatch.setattr(alerts, "_fetch_alerts", fake_fetch)
    monkeypatch.setattr(alerts, "_deactivate_alert", fake_deactivate)
    monkeypatch.setattr(alerts, "_db_available", lambda: True)
    return rows


def _quote_stub(prices: dict):
    def fake(tickers):
        return {
            "quotes": {
                t: ({"last_price": prices[t]} if t in prices else {"error": "no data"})
                for t in tickers
            },
            "as_of": "2026-08-16T12:00:00+00:00",
        }

    return fake


# ------------------------------- set -------------------------------


def test_set_alert_stores_and_returns_id(_fake_store):
    result = manage("set", ticker="RELIANCE.NS", level=1270.0, direction="below")
    assert result["alert_id"] == 1
    assert result["ticker"] == "RELIANCE.NS"
    assert "watch" in result["status"].lower() or "set" in result["status"].lower()


def test_set_rejects_bad_direction(_fake_store):
    result = manage("set", ticker="AAPL", level=100, direction="sideways")
    assert "error" in result


def test_set_rejects_missing_level(_fake_store):
    result = manage("set", ticker="AAPL", direction="above")
    assert "error" in result


def test_set_normalizes_ticker(_fake_store):
    result = manage("set", ticker=" reliance.ns ", level=1350, direction="above")
    assert result["ticker"] == "RELIANCE.NS"


# ------------------------------- list / delete -------------------------------


def test_list_shows_active_alerts(_fake_store):
    manage("set", ticker="AAPL", level=300, direction="below")
    manage("set", ticker="TCS.NS", level=2500, direction="above")
    result = manage("list")
    assert len(result["alerts"]) == 2


def test_delete_removes_alert(_fake_store):
    r = manage("set", ticker="AAPL", level=300, direction="below")
    result = manage("delete", alert_id=r["alert_id"])
    assert result["deleted"] is True
    assert manage("list")["alerts"] == []


def test_delete_unknown_id_is_clean_error(_fake_store):
    result = manage("delete", alert_id=999)
    assert "error" in result


# ------------------------------- check -------------------------------


def test_check_fires_below_alert_when_price_crosses(_fake_store):
    manage("set", ticker="RELIANCE.NS", level=1270, direction="below")
    with patch.object(alerts, "get_quotes", _quote_stub({"RELIANCE.NS": 1268.0})):
        result = manage("check")
    assert len(result["triggered"]) == 1
    t = result["triggered"][0]
    assert t["ticker"] == "RELIANCE.NS"
    assert t["current_price"] == 1268.0
    assert t["level"] == 1270


def test_check_does_not_fire_when_price_on_safe_side(_fake_store):
    manage("set", ticker="RELIANCE.NS", level=1270, direction="below")
    with patch.object(alerts, "get_quotes", _quote_stub({"RELIANCE.NS": 1310.0})):
        result = manage("check")
    assert result["triggered"] == []
    assert result["still_watching"] == 1


def test_check_fires_above_alert(_fake_store):
    manage("set", ticker="TCS.NS", level=2400, direction="above")
    with patch.object(alerts, "get_quotes", _quote_stub({"TCS.NS": 2450.0})):
        result = manage("check")
    assert len(result["triggered"]) == 1


def test_triggered_alert_is_one_shot(_fake_store):
    manage("set", ticker="AAPL", level=300, direction="above")
    with patch.object(alerts, "get_quotes", _quote_stub({"AAPL": 310.0})):
        first = manage("check")
        second = manage("check")
    assert len(first["triggered"]) == 1
    assert second["triggered"] == []


def test_check_with_unfetchable_ticker_keeps_alert_active(_fake_store):
    manage("set", ticker="DELISTED.NS", level=100, direction="below")
    with patch.object(alerts, "get_quotes", _quote_stub({})):
        result = manage("check")
    assert result["triggered"] == []
    assert result["still_watching"] == 1  # not silently dropped


def test_check_with_no_alerts_is_quiet(_fake_store):
    with patch.object(alerts, "get_quotes", _quote_stub({})):
        result = manage("check")
    assert result["triggered"] == []
    assert result["still_watching"] == 0


# ------------------------------- degradation -------------------------------


def test_no_database_is_clean_error(monkeypatch):
    monkeypatch.setattr(alerts, "_db_available", lambda: False)
    result = manage("set", ticker="AAPL", level=100, direction="below")
    assert "error" in result
    assert "DATABASE_URL" in result["error"]


def test_unknown_action_is_clean_error(_fake_store):
    result = manage("snooze")
    assert "error" in result


@pytest.mark.parametrize("owner", [None, "", "   "])
def test_missing_identity_fails_closed(owner):
    assert "Authenticated" in alerts.manage_alert("list", owner_id=owner)["error"]


@pytest.mark.parametrize("level", [float("nan"), float("inf"), -float("inf"), 0, -1])
def test_invalid_price_levels(level):
    assert "error" in manage("set", ticker="AAPL", level=level, direction="above")


def test_owner_cannot_list_delete_or_check_another_users_alerts():
    row = manage("set", ticker="AAPL", level=100, direction="above", owner_id="alice")
    assert manage("list", owner_id="bob")["alerts"] == []
    assert "error" in manage("delete", alert_id=row["alert_id"], owner_id="bob")
    with patch.object(alerts, "get_quotes", _quote_stub({"AAPL": 110})):
        assert manage("check", owner_id="bob")["triggered"] == []
        assert len(manage("check", owner_id="alice")["triggered"]) == 1


def test_losing_concurrent_poll_does_not_report_trigger(monkeypatch):
    manage("set", ticker="AAPL", level=100, direction="above")
    monkeypatch.setattr(alerts, "_deactivate_alert", lambda *a, **kw: False)
    with patch.object(alerts, "get_quotes", _quote_stub({"AAPL": 110})):
        assert manage("check")["triggered"] == []


@pytest.mark.parametrize("price", [float("nan"), float("inf"), -1, "broken"])
def test_invalid_quote_keeps_watching(price):
    manage("set", ticker="AAPL", level=100, direction="above")
    with patch.object(alerts, "get_quotes", _quote_stub({"AAPL": price})):
        result = manage("check")
    assert result["triggered"] == []
    assert result["still_watching"] == 1


def test_storage_errors_do_not_leak_credentials(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("postgres://secret:password@private-host")
    monkeypatch.setattr(alerts, "_fetch_alerts", fail)
    result = manage("list")
    assert "secret" not in str(result)
    assert "error" in result


@pytest.mark.parametrize("alert_id", [True, 1.9, -1, 0, float("inf"), None])
def test_delete_rejects_invalid_ids(alert_id):
    assert "error" in manage("delete", alert_id=alert_id)
