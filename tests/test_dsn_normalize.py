"""Tests for DSN normalization (handles unencoded special chars in passwords)."""

from core.telemetry import _normalize_dsn


def test_unencoded_at_in_password_is_encoded():
    dsn = "postgresql://postgres:Kandivali@67@db.abc.supabase.co:5432/postgres"
    out = _normalize_dsn(dsn)
    assert out == "postgresql://postgres:Kandivali%4067@db.abc.supabase.co:5432/postgres"


def test_already_encoded_password_is_unchanged():
    dsn = "postgresql://postgres:Kandivali%4067@db.abc.supabase.co:5432/postgres"
    assert _normalize_dsn(dsn) == dsn


def test_simple_password_untouched():
    dsn = "postgresql://postgres:simplepass@db.abc.supabase.co:5432/postgres"
    assert _normalize_dsn(dsn) == dsn


def test_pooler_style_username_preserved():
    dsn = "postgresql://postgres.abcdef:Pa$$w@rd@aws-0-us-west-2.pooler.supabase.com:6543/postgres"
    out = _normalize_dsn(dsn)
    assert out.startswith("postgresql://postgres.abcdef:")
    assert out.endswith("@aws-0-us-west-2.pooler.supabase.com:6543/postgres")
    assert "%40rd" in out


def test_hash_in_password_is_encoded():
    dsn = "postgresql://postgres:pa#ss@db.abc.supabase.co:5432/postgres"
    out = _normalize_dsn(dsn)
    assert "pa%23ss" in out


def test_non_url_dsn_passed_through():
    # keyword-style DSN should not be mangled
    dsn = "host=localhost port=5432 dbname=postgres user=postgres"
    assert _normalize_dsn(dsn) == dsn


def test_no_password_passed_through():
    dsn = "postgresql://postgres@db.abc.supabase.co:5432/postgres"
    assert _normalize_dsn(dsn) == dsn


def test_empty_and_none_safe():
    assert _normalize_dsn("") == ""
    assert _normalize_dsn(None) is None
