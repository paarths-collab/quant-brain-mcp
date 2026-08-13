"""Tests for the allowlist-backed legacy registry (stdio path)."""

from core.registry import register_all_tools


def test_registry_exposes_exactly_38_tools():
    tools = register_all_tools()
    assert len(tools) == 38


def test_registry_tool_names_are_get_functions():
    tools = register_all_tools()
    assert set(tools) >= {"get_rsi", "get_macd", "get_supertrend", "get_adx", "get_bbands"}
    assert all(name.startswith("get_") for name in tools)


def test_registry_excludes_non_core_indicators():
    tools = register_all_tools()
    for hidden in ("get_fwma", "get_ssf3", "get_pvr", "get_squeeze_pro", "get_mom"):
        assert hidden not in tools


def test_registry_entries_have_full_metadata():
    tools = register_all_tools()
    for name, info in tools.items():
        assert callable(info["func"]), name
        assert info["description"].strip(), name
        params = info["parameters"]
        assert params["required"] == ["ticker"], name
        assert "ticker" in params["properties"], name
