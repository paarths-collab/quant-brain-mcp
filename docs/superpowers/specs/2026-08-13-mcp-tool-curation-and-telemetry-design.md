# MCP Tool Curation + Usage Telemetry — Design

- **Date:** 2026-08-13
- **Status:** Approved for planning (pending user review of this doc)
- **Scope:** `mcp-quant-brain` (deployed FastMCP HTTP server on Render)

## 1. Problem & Goals

The server auto-registers **133 unique indicators** as individual MCP tools by
walking the entire `tools/` tree (`core/registry.py::register_all_tools`). This
bloats the tool surface, makes tool selection hard for AI clients, and the
README's "150+ indicators" is both unimpressive positioning and inaccurate.

There is also **no usage telemetry**, so success is measured by feature count
rather than real KPIs. Any in-memory counters would be wiped on every Render
restart.

**Goals**

1. Shrink the public MCP surface to **38 curated indicators** exposed through
   **6 grouped tools** via an explicit allowlist (no tree-walking).
2. Instrument **every** MCP tool call with telemetry:
   `tool_name, session_id, duration_ms, success, tool_category`.
3. Persist telemetry in **Postgres/Supabase** (survives restarts).
4. Add a bearer-protected **`GET /metrics/summary`** returning resume-ready KPIs.

**Non-goals**

- No change to optimization/backtest/chart/intelligence tool behavior.
- No per-indicator parameter tuning through the grouped tools in v1 (defaults only).
- No physical deletion/relocation of internal/archive indicator modules (allowlist
  hides them; files stay put).
- The legacy stdio server (`main.py`) is not the deployment target; it inherits the
  shrunk registry for consistency but is otherwise out of scope.

**Resume positioning (replaces "150+ indicators"):**
> 38 curated quantitative indicators • 7 portfolio optimizers • 8 backtesting
> workflows • U.S. + Indian equities • production usage telemetry

KPI framing: **X+ MCP requests • Y+ unique sessions • Z+ backtests/optimizations
• 98%+ success rate • p95 latency**.

---

## 2. Change 1 — Indicator curation (38 core, 6 grouped tools)

### 2.1 Tiering

- **Core (38):** exposed via 6 grouped tools (below).
- **Internal (69):** remain importable for research/backtesting; not exposed.
- **Archive (26):** remain in place; not exposed. (Decision: leave files where they
  are — the allowlist already removes them from the surface.)

Aroon is currently duplicated (`momentum/aroon.py` + `trend/aroon.py`). Canonical =
`trend/aroon.py`; `momentum/aroon.py` becomes redundant and stays unexposed.

### 2.2 The 6 grouped tools → 38 core indicators

Every entry maps to an existing `tools/indicators/<area>/<module>.py` exposing
`get_<module>` (all 38 verified to resolve):

| Grouped tool | Area | Indicators (module keys) |
|---|---|---|
| `analyze_momentum` | momentum | rsi, macd, roc, cci, stoch, stochrsi, tsi, willr |
| `analyze_technical_levels` | overlap | sma, ema, hma, kama, ichimoku, supertrend, vwap, vwma |
| `analyze_trend` | trend | adx, aroon *(trend)*, chop, psar, vortex, zigzag |
| `analyze_volatility` | volatility | atr, bbands, donchian, kc, stdev, ui |
| `analyze_volume` | volume | obv, cmf, mfi, ad, pvt |
| `analyze_statistics` | misc | log_return, zscore, skew, kurtosis, entropy |

Count: 8 + 8 + 6 + 6 + 5 + 5 = **38**.

### 2.3 Grouped tool contract

```python
analyze_momentum(ticker: str, indicators: list[str] | None = None) -> dict
```

- `indicators=None` → run the entire group; otherwise run the named subset.
- Unknown keys are ignored and reported under `unknown_indicators`.
- Data is fetched **once** per call via `core.data_loader.fetch_data`.
- Each indicator runs under its own `try/except`; a failure yields
  `{"error": "..."}` in that indicator's slot instead of failing the whole group.
- v1 uses each indicator's default parameters (matches today's per-indicator tools).

Return shape:

```json
{
  "ticker": "AAPL",
  "group": "momentum",
  "indicators": {
    "rsi": { "...": "..." },
    "macd": { "...": "..." }
  },
  "unknown_indicators": []
}
```

### 2.4 Explicit allowlist registry

New file `core/indicator_registry.py` is the single source of truth:

```python
# key -> (module_path, func_name)   grouped by tool
INDICATOR_GROUPS = {
    "momentum": {"tool": "analyze_momentum", "indicators": {
        "rsi": ("tools.indicators.momentum.rsi", "get_rsi"),
        ...
    }},
    ...
}
```

- Modules are **lazily imported** on first use (Render cold-start friendly).
- Helper `run_group(group, ticker, indicators)` implements §2.3 and is shared by the
  MCP tool wrappers.

`core/registry.py::register_all_tools()` is **rewritten** from tree-walking to build
its flat `{tool_name: {...}}` dict from `INDICATOR_GROUPS` (allowlist). This keeps the
legacy `main.py` stdio path working while shrinking it 133 → 38 for consistency.

In `fastmcp_server.py`, `_register_dynamic_tools()` is **replaced** by
`_register_indicator_group_tools()`, which registers the 6 grouped tools (each wrapped
with telemetry — see §3).

---

## 3. Change 2 — Telemetry on every tool call

### 3.1 One decorator to register + instrument

New file `core/telemetry.py` exposes a decorator used **in place of** `@mcp.tool()`:

```python
@tracked_tool("optimization")
def optimize_mvo(...): ...
```

`tracked_tool(category)` = `lambda fn: mcp.tool()(_instrument(fn, category))`.
Registering through this single entry point means **no tool can be added without
telemetry**. `_instrument` uses `functools.wraps`, so FastMCP's signature/`inputSchema`
introspection (which follows `__wrapped__`) is preserved.

Placement (fixed): `core/telemetry.py` owns all measurement + the writer and exposes
`instrument(fn, category)` plus `record(event)`. `fastmcp_server.py` (which creates
`mcp`) defines the thin `tracked_tool(category)` that closes over `mcp`:
`lambda fn: mcp.tool()(instrument(fn, category))`. This keeps `core/telemetry.py` free
of any import of `mcp` the instance, avoiding a circular import.

### 3.2 Captured fields

| Field | Source |
|---|---|
| `tool_name` | wrapped function `__name__` |
| `tool_category` | decorator argument |
| `session_id` | see §3.3 |
| `duration_ms` | `time.perf_counter()` delta around the call |
| `success` | see §3.4 |
| `error` | exception/`error` string (nullable, for debugging) |
| `ts` | DB default `now()` |

### 3.3 session_id derivation

At call time, read the Starlette request via
`mcp.get_context().request_context.request`:

1. `request.headers["mcp-session-id"]` if present.
2. Else fingerprint: `"fp_" + sha1(client_ip + "|" + user_agent).hexdigest()[:16]`.
3. Else `"unknown"`.

The whole derivation is wrapped in `try/except → "unknown"` and can **never** break a
tool call. (Rationale: the server runs `stateless_http=True`, so no session id is
assigned server-side; the fingerprint is a stable per-client proxy for "unique
sessions".)

### 3.4 success semantics

`success = True` only if the call raised **no** exception **and** the return value is
not a dict containing an `"error"` key. This counts the codebase's soft-error
convention (`return {"error": ...}`) as a failure, keeping success-rate honest.
Exceptions are recorded as `success=False` and **re-raised** so the client still sees
them.

### 3.5 Fire-and-forget writer (telemetry never blocks tools)

`core/telemetry.py` owns a module-level singleton writer:

- Events pushed to a bounded `queue.Queue(maxsize=10000)` via `put_nowait`.
- A single **daemon thread** drains the queue and inserts into Postgres (psycopg2),
  reconnecting on failure with backoff.
- Queue full → drop the event, increment a `dropped` counter, log at most periodically.
- All DB errors are caught and logged; they never propagate to the tool path.
- If `DATABASE_URL` is unset, the writer is disabled (no-op) and logs once — clean
  local dev with zero DB.

---

## 4. Change 3 — Postgres/Supabase storage

### 4.1 Schema

```sql
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
```

### 4.2 Connection & provisioning

- Connection string from env `DATABASE_URL` (psycopg2). For Supabase use the
  **Session pooler** URI with `sslmode=require`.
- **Provisioning (Supabase, chosen):** during implementation, create the table in the
  connected Supabase project via the Supabase MCP (`apply_migration`).
- **Safety net:** the writer also runs `CREATE TABLE IF NOT EXISTS` + indexes on first
  successful connect, so a fresh/generic Postgres is turnkey.
- `requirements.txt`: add `psycopg2-binary`. (SQLAlchemy not required; raw psycopg2.)

### 4.3 Tool category taxonomy

| Category | Tools |
|---|---|
| `indicator` | the 6 `analyze_*` grouped tools |
| `optimization` | `generate_optimized_verdict`, `optimize_{mvo,hrp,max_sharpe,min_volatility,black_litterman,cvar,semivariance}` |
| `backtest` | `backtest_{macd_momentum,macd_trend_follower,mean_reversion_rsi_bb,rsi_mean_reversion,sma_crossover,trend_crossover,volatility_breakout,universal_indicator}` |
| `chart` | `generate_chart_pack`, `generate_charts`, `plot_charts` |
| `intelligence` | `get_company_profile`, `find_sector_stock_pipeline_tool`, `analyze_sector_intelligence_tool` |

`backtests` / `optimizations` in the metrics endpoint are derived from these
categories.

---

## 5. Change 4 — `GET /metrics/summary`

### 5.1 Auth (fails closed)

Bearer token: request must send `Authorization: Bearer <METRICS_TOKEN>`.
- Wrong/missing header → **401**.
- `METRICS_TOKEN` env unset → **503** (fails closed; never accidentally public).

### 5.2 Aggregation (single SQL pass)

```sql
SELECT
  count(*)                                                             AS total_requests,
  count(DISTINCT session_id)                                          AS unique_sessions,
  count(*) FILTER (WHERE tool_category = 'backtest')                  AS backtests,
  count(*) FILTER (WHERE tool_category = 'optimization')              AS optimizations,
  avg(CASE WHEN success THEN 1.0 ELSE 0.0 END)                       AS success_rate,
  percentile_cont(0.5)  WITHIN GROUP (ORDER BY duration_ms)          AS p50_latency,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms)          AS p95_latency
FROM mcp_tool_events;
```

The blocking query runs inside the async route via `asyncio.to_thread`.

### 5.3 Response

```json
{
  "total_requests": 0,
  "unique_sessions": 0,
  "backtests": 0,
  "optimizations": 0,
  "success_rate": null,
  "p50_latency": null,
  "p95_latency": null,
  "latency_unit": "ms",
  "generated_at": "2026-08-13T00:00:00Z"
}
```

- Field names match the request exactly; `latency_unit` + `generated_at` added for
  clarity. `success_rate` is a fraction (0–1); latencies are milliseconds, rounded to
  1 decimal.
- Empty table → `total_requests`, `unique_sessions`, `backtests`, `optimizations` are
  `0`; `success_rate`, `p50_latency`, `p95_latency` are `null`. `DATABASE_URL` unset → 503.

---

## 6. Config, deploy, docs

- **`render.yaml`**: add `DATABASE_URL` and `METRICS_TOKEN` as `sync: false` secrets
  (set in the Render dashboard).
- **`requirements.txt`**: add `psycopg2-binary`.
- **`README.md`**: remove "150+ technical indicators"; add the repositioning line
  (§1), document the 6 grouped tools, `/metrics/summary`, and the two env vars.
- **`.env`** already gitignored — no secrets committed.

---

## 7. Testing strategy

1. **Registry allowlist:** `register_all_tools()` returns exactly 38 keys; the 6
   groups sum to 38; `momentum/aroon` is absent, `trend/aroon` present.
2. **Grouped tools:** `analyze_momentum("AAPL")` returns all 8 slots; subset selection
   works; a forced indicator error is isolated to its slot; unknown keys land in
   `unknown_indicators`. (Data-fetch mocked to avoid network in unit tests.)
3. **Tool schemas intact:** listing tools yields correct `inputSchema` for a
   `tracked_tool`-wrapped tool (proves `functools.wraps` signature preservation).
4. **Telemetry unit:** `success` semantics (exception, `{"error":...}`, ok);
   `session_id` fallbacks; writer no-ops when `DATABASE_URL` unset; queue-full drops
   without raising.
5. **Storage (integration, optional/skipped without DB):** insert → row present with
   all fields.
6. **Endpoint:** 401 wrong token, 503 unset token, 200 shape with token; empty-table
   nulls; category counts correct against seeded rows.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Decorator breaks FastMCP schema generation | `functools.wraps` preserves signature; test #3 asserts it before ship. |
| DB latency/outage slows or breaks tool calls | Fire-and-forget queue + daemon writer; all DB errors swallowed; tools never await the DB. |
| Supabase SSL/pooler connection quirks on Render | Use Session-pooler URI + `sslmode=require`; document exact format; `CREATE TABLE IF NOT EXISTS` safety net. |
| `session_id` weak in stateless mode | Header-first, IP+UA fingerprint fallback; documented as a unique-session proxy. |
| Hidden internal modules still imported somewhere | Allowlist only changes exposure, not importability; files stay in place, so imports keep working. |

---

## 9. File-by-file change list

| File | Change |
|---|---|
| `core/indicator_registry.py` | **New.** Allowlist of 38 core in 6 groups; `run_group()` helper. |
| `core/telemetry.py` | **New.** `tracked_tool`/instrument, session_id, queue + daemon writer, schema bootstrap. |
| `core/registry.py` | Rewrite `register_all_tools()` to read the allowlist (133 → 38). |
| `fastmcp_server.py` | Replace `_register_dynamic_tools()` with 6 grouped tools; convert all `@mcp.tool()` → `@tracked_tool("<category>")`; add `/metrics/summary` route. |
| `requirements.txt` | Add `psycopg2-binary`. |
| `render.yaml` | Add `DATABASE_URL`, `METRICS_TOKEN` (`sync: false`). |
| `README.md` | Reposition; document grouped tools, metrics endpoint, env vars. |
| `tests/…` | New unit tests per §7. |

Supabase table provisioned via MCP during implementation (not a repo file).
