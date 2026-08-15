# MCP Tool Curation + Telemetry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 133 auto-registered indicator tools with 6 grouped tools over a 38-indicator allowlist; add per-call telemetry persisted to Supabase Postgres; expose a bearer-protected `/metrics/summary`.

**Architecture:** New `core/indicator_registry.py` (allowlist + `run_group`) and `core/telemetry.py` (instrument + queue + daemon writer). `fastmcp_server.py` defines `tracked_tool(category)` = `mcp.tool()` ∘ `instrument`, registers 6 grouped tools, adds the metrics route. `core/registry.py` becomes an allowlist reader for the legacy stdio path.

**Tech Stack:** Python 3.12, FastMCP (mcp 1.26), psycopg2-binary, Supabase Postgres, pytest.

Spec: `docs/superpowers/specs/2026-08-13-mcp-tool-curation-and-telemetry-design.md`

---

### Task 1: `core/indicator_registry.py` (allowlist + run_group) — TDD

**Files:** Create `core/indicator_registry.py`, `tests/test_indicator_registry.py`

- [ ] Write failing tests: 38 total keys; groups sum 8/8/6/6/5/5; `run_group` returns per-indicator slots, isolates a failing indicator, reports unknown keys, fetches data once (mock).
- [ ] Implement:

```python
INDICATOR_GROUPS = {
  "momentum": {"tool": "analyze_momentum", "indicators": {
    "rsi": ("tools.indicators.momentum.rsi", "get_rsi"),
    "macd": ("tools.indicators.momentum.macd", "get_macd"),
    "roc": ("tools.indicators.momentum.roc", "get_roc"),
    "cci": ("tools.indicators.momentum.cci", "get_cci"),
    "stoch": ("tools.indicators.momentum.stoch", "get_stoch"),
    "stochrsi": ("tools.indicators.momentum.stochrsi", "get_stochrsi"),
    "tsi": ("tools.indicators.momentum.tsi", "get_tsi"),
    "willr": ("tools.indicators.momentum.willr", "get_willr")}},
  "technical_levels": {"tool": "analyze_technical_levels", "indicators": {
    "sma": ("tools.indicators.overlap.sma", "get_sma"),
    "ema": ("tools.indicators.overlap.ema", "get_ema"),
    "hma": ("tools.indicators.overlap.hma", "get_hma"),
    "kama": ("tools.indicators.overlap.kama", "get_kama"),
    "ichimoku": ("tools.indicators.overlap.ichimoku", "get_ichimoku"),
    "supertrend": ("tools.indicators.overlap.supertrend", "get_supertrend"),
    "vwap": ("tools.indicators.overlap.vwap", "get_vwap"),
    "vwma": ("tools.indicators.overlap.vwma", "get_vwma")}},
  "trend": {"tool": "analyze_trend", "indicators": {
    "adx": ("tools.indicators.trend.adx", "get_adx"),
    "aroon": ("tools.indicators.trend.aroon", "get_aroon"),
    "chop": ("tools.indicators.trend.chop", "get_chop"),
    "psar": ("tools.indicators.trend.psar", "get_psar"),
    "vortex": ("tools.indicators.trend.vortex", "get_vortex"),
    "zigzag": ("tools.indicators.trend.zigzag", "get_zigzag")}},
  "volatility": {"tool": "analyze_volatility", "indicators": {
    "atr": ("tools.indicators.volatility.atr", "get_atr"),
    "bbands": ("tools.indicators.volatility.bbands", "get_bbands"),
    "donchian": ("tools.indicators.volatility.donchian", "get_donchian"),
    "kc": ("tools.indicators.volatility.kc", "get_kc"),
    "stdev": ("tools.indicators.volatility.stdev", "get_stdev"),
    "ui": ("tools.indicators.volatility.ui", "get_ui")}},
  "volume": {"tool": "analyze_volume", "indicators": {
    "obv": ("tools.indicators.volume.obv", "get_obv"),
    "cmf": ("tools.indicators.volume.cmf", "get_cmf"),
    "mfi": ("tools.indicators.volume.mfi", "get_mfi"),
    "ad": ("tools.indicators.volume.ad", "get_ad"),
    "pvt": ("tools.indicators.volume.pvt", "get_pvt")}},
  "statistics": {"tool": "analyze_statistics", "indicators": {
    "log_return": ("tools.indicators.misc.log_return", "get_log_return"),
    "zscore": ("tools.indicators.misc.zscore", "get_zscore"),
    "skew": ("tools.indicators.misc.skew", "get_skew"),
    "kurtosis": ("tools.indicators.misc.kurtosis", "get_kurtosis"),
    "entropy": ("tools.indicators.misc.entropy", "get_entropy")}},
}

def _resolve(module_path, func_name):  # lazy import
    import importlib
    return getattr(importlib.import_module(module_path), func_name)

def iter_all_indicators():  # -> (key, module_path, func_name, group)
    for group, spec in INDICATOR_GROUPS.items():
        for key, (mp, fn) in spec["indicators"].items():
            yield key, mp, fn, group

def run_group(group: str, ticker: str, indicators=None) -> dict:
    from core.data_loader import fetch_data
    from utils.serializer import serialize_output
    spec = INDICATOR_GROUPS[group]
    available = spec["indicators"]
    requested = list(available) if not indicators else [str(i).lower() for i in indicators]
    unknown = [k for k in requested if k not in available]
    selected = [k for k in requested if k in available]
    df, err = fetch_data(ticker)
    if err:
        return {"ticker": ticker, "group": group, "error": err,
                "indicators": {}, "unknown_indicators": unknown}
    out = {}
    for key in selected:
        mp, fn = available[key]
        try:
            out[key] = serialize_output(_resolve(mp, fn)(df))
        except Exception as exc:
            out[key] = {"error": f"{key} failed: {exc}"}
    return {"ticker": ticker, "group": group, "indicators": out,
            "unknown_indicators": unknown}
```

- [ ] `pytest tests/test_indicator_registry.py -v` → PASS. Commit.

### Task 2: Rewrite `core/registry.py` from allowlist — TDD

**Files:** Modify `core/registry.py`, create `tests/test_registry.py`

- [ ] Failing tests: exactly 38 tools; `get_aroon` maps to trend module; every entry has func/description/parameters with required ticker.
- [ ] Replace tree-walk with:

```python
def register_all_tools():
    from core.indicator_registry import iter_all_indicators, _resolve
    tools = {}
    for key, mp, fn, group in iter_all_indicators():
        try:
            func = _resolve(mp, fn)
        except Exception:
            continue
        import importlib
        doc = (importlib.import_module(mp).__doc__ or func.__doc__ or "").strip() or (
            f"Technical analysis tool for {key.upper()} ({group}).")
        tools[fn] = {"func": func, "description": doc, "parameters": {
            "type": "object",
            "properties": {"ticker": {"type": "string", "description": "Stock ticker (e.g., AAPL or RELIANCE.NS)"}},
            "required": ["ticker"]}}
    return tools
```

- [ ] Tests pass. Commit.

### Task 3: `core/telemetry.py` — TDD

**Files:** Create `core/telemetry.py`, `tests/test_telemetry.py`

- [ ] Failing tests: `instrument` preserves `__name__`/signature; success semantics (ok → True, `{"error":...}` → False, exception → False + re-raise); no-op without `DATABASE_URL`; queue-full drops silently; session-id fallback returns `"unknown"` outside request context.
- [ ] Implement: `TelemetryWriter` singleton (bounded `queue.Queue(10000)`, daemon thread, psycopg2 connect w/ retry, `CREATE TABLE IF NOT EXISTS` + 3 indexes on connect, batch `executemany` drain, all errors swallowed); `derive_session_id(ctx)` per spec §3.3; `instrument(fn, category, get_context)`:

```python
def instrument(fn, category, get_context=None):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        success, error = True, None
        try:
            result = fn(*args, **kwargs)
            if isinstance(result, dict) and "error" in result:
                success, error = False, str(result["error"])[:500]
            return result
        except Exception as exc:
            success, error = False, str(exc)[:500]
            raise
        finally:
            try:
                record(Event(tool_name=fn.__name__, tool_category=category,
                             session_id=derive_session_id(get_context),
                             duration_ms=(time.perf_counter() - t0) * 1000.0,
                             success=success, error=error))
            except Exception:
                pass
    return wrapper
```

- [ ] Tests pass. Commit.

### Task 4: Rewire `fastmcp_server.py`

**Files:** Modify `fastmcp_server.py`, create `tests/test_server_tools.py`

- [ ] Failing test: listed tool names == expected 27-tool set (6 analyze_* + 8 optimize/verdict + 8 backtest + 3 chart + 3 intelligence, minus overlaps = exact set asserted); `analyze_momentum` schema has `ticker` required + `indicators` optional.
- [ ] Define after `mcp = FastMCP(...)`:

```python
from core import telemetry
def tracked_tool(category: str):
    def deco(fn):
        return mcp.tool()(telemetry.instrument(fn, category, mcp.get_context))
    return deco
```

- [ ] Convert every existing `@mcp.tool()` → `@tracked_tool("<category>")` per spec §4.3 taxonomy.
- [ ] Delete `_register_dynamic_tools()`; add explicit 6 grouped tools (explicit defs so schemas are clean):

```python
@tracked_tool("indicator")
def analyze_momentum(ticker: str, indicators: list[str] | None = None) -> dict:
    """Momentum indicators: rsi, macd, roc, cci, stoch, stochrsi, tsi, willr. Omit `indicators` to run all."""
    return run_group("momentum", ticker, indicators)
# ... same for technical_levels, trend, volatility, volume, statistics
```

- [ ] Add `/metrics/summary` custom route: bearer check (`METRICS_TOKEN` unset → 503; wrong/missing → 401), aggregate SQL from spec §5.2 via `asyncio.to_thread(telemetry.fetch_summary)`, JSON response per §5.3.
- [ ] Tests pass; `python -c "import fastmcp_server"` clean. Commit.

### Task 5: Config + deps + Supabase provisioning

**Files:** Modify `requirements.txt`, `render.yaml`

- [ ] Add `psycopg2-binary` to requirements. Add to render.yaml envVars: `DATABASE_URL` and `METRICS_TOKEN` with `sync: false`.
- [ ] Provision Supabase: `apply_migration` with spec §4.1 SQL against the user's project (confirm project first via `list_projects`).
- [ ] Commit.

### Task 6: README repositioning

**Files:** Modify `README.md`

- [ ] Replace "150+ technical indicators" with "38 curated quantitative indicators exposed through 6 grouped analysis tools"; update Core Tools section (list the 6 `analyze_*` tools, drop `get_rsi`-style names); add positioning line and `/metrics/summary` + env var docs.
- [ ] Commit.

### Task 7: Full verification

- [ ] `pytest -q` all green.
- [ ] Smoke: run server locally (`uvicorn render_app:app --port 8000`), check `/health`, `/metrics/summary` auth behavior (503 without token env, 401 wrong token, 200 with token + DATABASE_URL), and an MCP `tools/list` shows 27 tools.
- [ ] Final commit; offer push to trigger Render deploy.
