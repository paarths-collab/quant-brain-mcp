# Architecture and methodology

Quant Brain is a Python MCP server for market data, calculations and personal Indian-equity research. A client such as Claude can call individual tools or request a background investigation. The research service runs bounded Codex specialist turns, stores a report, and returns it to the client for interpretation. It does not place orders.

For installation, authentication and Claude connection commands, see the [research runtime guide](research-runtime.md). For hosted HTTP configuration, see [deployment](deployment.md).

## System architecture

```mermaid
flowchart TB
    Client["Claude or another MCP client"]
    subgraph Outer["Outer server: render_app:app · port 8000"]
        Auth["Bearer authentication<br/>owner identity and request limits"]
        Public["29 public MCP tools<br/>25 analysis/alert tools + 4 research tools"]
        Jobs["Research service<br/>one job worker and bounded queue"]
    end
    subgraph Local["Local research runtime"]
        Codex["Codex SDK specialist turns<br/>selected local sign-in profile"]
        Internal["Internal MCP: internal_app:app<br/>loopback port 8001 · separate bearer token<br/>21 allowed analysis tools"]
        SQLite[("SQLite<br/>jobs, progress events, reports")]
    end
    Calc["Shared Python calculation and data tools"]
    Yahoo["Yahoo Finance via yfinance"]
    Search["Hosted live web search"]
    PG[("Optional PostgreSQL<br/>alerts and telemetry")]
    Client -->|"Streamable HTTP /mcp"| Auth
    Auth --> Public
    Public -->|"start / status / report / cancel"| Jobs
    Jobs <--> SQLite
    Jobs --> Codex
    Codex --> Search
    Codex --> Internal
    Internal --> Calc
    Public --> Calc
    Calc --> Yahoo
    Public --> PG
    Internal -. "tool telemetry, if configured" .-> PG
```

The two MCP surfaces use the same calculation implementations. The internal surface excludes research orchestration, alert operations and chart tools. Internal researchers therefore cannot recursively start more research jobs or mutate alerts through their MCP tool catalog.

The outer server uses FastMCP's stateless HTTP transport. Research jobs are independent of individual HTTP requests: reconnecting or polling does not end a job. SQLite retains completed reports, but an interrupted job is marked failed on recovery; it is not resumed from its last agent turn.

## Research agents and bounded workflow

The agents are roles implemented by separate Codex turns, not six permanently running services. Python controls their ordering and budgets. Each turn uses a temporary working directory and an ephemeral Codex thread. Model selection is configurable with `QUANT_CODEX_MODEL`; an unset value uses the runtime default.

| Role | Responsibility |
|---|---|
| Lead | Define a focused investigation plan. |
| Company analyst | Research the business, results, announcements and material news. |
| Quant analyst | Use calculation tools for returns, comparisons and risk; disclose periods and assumptions. |
| Skeptic | Challenge the investment argument and retain contradictory evidence. |
| Auditor | Review original claim IDs for source support, freshness, units and calculations; request corrections. |
| Synthesizer | Select existing claims, summarize the audit and preserve disagreements. |

```mermaid
flowchart TD
    Start["Validated NSE research request"] --> Mode{"Depth"}
    Mode -->|"standard / deep"| Lead["Lead plans investigation"]
    Mode -->|"quick"| Parallel
    Lead --> Parallel
    subgraph Parallel["Parallel analysis"]
        Company["Company analyst"]
        Quant["Quant analyst"]
    end
    Parallel --> Check{"Quick mode?"}
    Check -->|"yes"| Audit["Auditor reviews prior claims"]
    Check -->|"no"| Skeptic["Skeptic challenges findings"]
    Skeptic --> Audit
    Audit --> Correction{"Correction requested<br/>and budget remains?"}
    Correction -->|"yes"| Repair["Company role performs cross-disciplinary correction<br/>including recalculation where needed"]
    Repair --> Audit
    Correction -->|"no"| Synthesis["Synthesizer selects existing claims"]
    Synthesis --> Validate["Schema, citation and audit consistency checks"]
    Validate --> Report["Persist report, warnings and execution trace"]
```

| Depth | Role invocations | Correction budget |
|---|---:|---|
| `quick` | 4 | None: company + quant, auditor, synthesizer. |
| `standard` | 6–8 | Up to one correction and repeat audit. |
| `deep` | 6–10 | Up to two corrections and repeat audits. |

Only company and quant run concurrently. If either fails, the sibling task is cancelled. A correction pass uses the company role with additional instructions to address all audit challenges, including quant errors.

Default limits are 120 seconds per role and 900 seconds per job. `QUANT_CODEX_ROLE_TIMEOUT` accepts 1–600 seconds; the job deadline still applies. At most four queued/running jobs are accepted globally and two per authenticated owner. One job executes at a time. These are invocation, time and queue limits, not a monetary spending cap or a fixed tool-call budget.

## Request and job lifecycle

```mermaid
sequenceDiagram
    participant C as Claude / MCP client
    participant M as Outer MCP
    participant J as Job worker
    participant S as SQLite
    participant R as Codex role turns
    participant T as Internal MCP / web search
    C->>M: start_research(question, tickers, depth)
    M->>M: Authenticate owner and validate input/capacity
    M->>S: Create queued job
    M-->>C: Job ID and status
    M->>J: Schedule background work
    J->>S: Mark running and save stage events
    J->>R: Invoke bounded role workflow
    R->>T: Retrieve evidence and run calculations
    T-->>R: Results and limitations
    loop While job is active
        C->>M: get_research_status(job_id)
        M->>S: Read job for authenticated owner
        M-->>C: Current status and stage
    end
    R-->>J: Structured findings and observed tool events
    J->>J: Validate and assemble report
    J->>S: Store completed report
    C->>M: get_research_report(job_id)
    M->>S: Read completed report for owner
    M-->>C: Report, warnings and events
    Note over C,M: Client interprets the report and explains uncertainty
```

```mermaid
stateDiagram-v2
    [*] --> queued: Accepted
    queued --> running: Worker starts
    queued --> cancelled: Owner cancels
    running --> cancelled: Owner cancels or active task stops at shutdown
    running --> completed: Valid report stored
    running --> failed: Timeout / provider / tool / validation failure
    queued --> failed: Interrupted work recovered
    running --> failed: Interrupted work recovered
    completed --> [*]
    cancelled --> [*]
    failed --> [*]
```

Terminal states are immutable. Cancellation stops queued work or requests cancellation of the active async workflow and closes the Codex client. It cannot refund model usage already incurred. A synchronous calculation already running in a thread may finish after cancellation; its capacity slot remains held until that thread exits.

An exclusive worker lock allows one outer server worker per research database. ASGI server shutdown closes the job service; FastMCP's per-request lifespan does not. On restart, queued/running records left behind become failed with an interruption message. Starting a fresh job is the recovery mechanism.

## Authentication and trust boundaries

| Boundary | Current behavior |
|---|---|
| Client → outer `/mcp` | `MCP_API_KEYS` maps stable owner IDs to SHA-256 token digests. Missing configuration fails closed. Request parameters cannot choose the authenticated owner. |
| Research/alert ownership | Lookups and mutations are scoped to the authenticated owner. A different owner cannot retrieve a job by knowing its ID. |
| Codex → internal `/mcp` | Separate `QUANT_INTERNAL_TOKEN`, minimum 32 characters, and an explicit 21-tool allowlist. Bind this server to loopback. |
| Codex sign-in | The official runtime handles credentials in the selected `QUANT_CODEX_HOME`. The application does not read or copy credential files. A dedicated profile is the default; an existing profile can be selected explicitly. |
| Inherited local integrations | Runtime overrides clear inherited MCP/plugin tables and disable shell, unified execution, apps, plugins, browser/computer use, host skill discovery and recursive multi-agent features. Live web search and the internal MCP remain available. |
| External evidence | Role instructions treat pages, documents and tool output as untrusted evidence. Model compliance with those instructions is not a proof against prompt injection. |
| Metrics | `/metrics/summary` has its own `METRICS_TOKEN`; `/health` is a basic public process check. Neither proves research/model readiness. |

The outer `/mcp` default is 60 requests per minute per owner with four admitted requests per process. The internal surface uses 120 requests per minute and the same default concurrency limit. Both limit request bodies to 1 MiB and body reads to 15 seconds. Browser requests with an `Origin` header require an explicit `MCP_ALLOWED_ORIGINS` match. These controls are per process, not distributed limits.

For remote hosting, configure HTTPS and ingress restrictions as described in [deployment](deployment.md). Keep Codex profiles, runtime environment files, token material, databases and captured research outside the repository. There is no Google OAuth requirement for this local design: the outer MCP bearer credential and the Codex sign-in are separate.

## Evidence and report contract

Each claim references evidence IDs. Evidence contains a source URL or an allowed `urn:tool:quant_internal:<tool_name>`, title, excerpt, retrieval time and optional publication time. Calculation claims require a method. Strict schemas reject unknown fields, conflicting IDs and dangling references. The synthesizer cannot introduce new claim or evidence IDs or alter an existing claim under the same ID.

The latest auditor's assessment bounds the final report. Missing audit support, unresolved correction requests or empty supported conclusions produce `insufficient_evidence` and low confidence. The final confidence cannot exceed the auditor's confidence. Earlier warnings and disagreements remain in the report.

**Verification is model review.** `verification_basis` is explicitly `model_review`. The SDK execution trace records observed web-search events and allowed MCP call names/statuses without prompts, arguments, results or URLs. It shows which tool activity occurred, but does not bind a particular source excerpt or numeric claim to a particular retrieved result. A tool URN identifies a tool; it does not prove execution or factual correctness. Dates and excerpts supplied by a model also require independent checking. Successful tests and agent agreement do not establish investment accuracy.

## Data and calculation conventions

| Area | Convention or limitation |
|---|---|
| Research market | 1–5 NSE symbols, normalized to `.NS`; reports identify INR and `Asia/Kolkata`. Individual analysis tools may support additional markets. |
| Historical bars | Shared yfinance loaders request `auto_adjust=True`, incorporating dividend/split adjustments in OHLC prices. |
| Quote freshness | `as_of` and `fetched_at` are retrieval times. The quote tool returns `market_timestamp: null` and `freshness_status: unknown`; retrieval time is not an exchange observation time. Provider delay notes are not a freshness guarantee. |
| Annualization | 252 trading days for the shared trading-year convention. |
| Backtests | Inspect each response's benchmark, sample period and cost assumptions. Strategy backtests and portfolio holdout evaluation do not share identical cost models. |
| Web search | Research evidence, not an exchange-grade live-price feed. |
| Missing data | Provider outages, stale observations and incomplete inputs can make a result unavailable or insufficient. |

Portfolio optimization fits weights on the earliest 70% of aligned history and evaluates frozen weights on the latest 30%. It requires at least 126 training and 63 holdout observations. Purchases occur at the first holdout close; no return is credited across the training boundary. Returned weights are the historical training allocation, not a refit on all available data.

The historical verdict uses holdout performance only. Full-history alpha and risk fields are descriptive diagnostics and cannot upgrade that verdict. Response metadata discloses dates and unmodeled costs. A single holdout is not walk-forward validation or evidence of future returns.

## Storage and observability

| Store | Contents and behavior |
|---|---|
| SQLite (`QUANT_RESEARCH_DB`) | Owner-scoped questions, symbols, status, progress events and completed reports. WAL mode; newly created database files use private permissions. Persistence needs a durable filesystem. No automatic retention/deletion policy is implemented. |
| Optional PostgreSQL (`DATABASE_URL`) | Persistent price alerts and tool telemetry. Research jobs do not depend on PostgreSQL. |
| Telemetry queue | Bounded in-process queue with a background PostgreSQL writer. Delivery is best effort; queue overflow or storage failure can lose events. |

Tool telemetry includes name, category, duration, success, a truncated error when present, and a session identifier. The identifier is an MCP session header when available or a hash derived from client IP and user agent. This is not a guarantee of anonymous data: errors and session metadata should be treated as potentially sensitive. The instrumentation is designed to keep telemetry failures from failing tool calls.

The research execution trace is separate from tool telemetry. It is saved with a completed report; failed jobs expose safe error messages and stage events rather than a guaranteed complete execution trace.

## Repository map

```text
render_app.py              Outer authenticated ASGI app and server lifecycle
fastmcp_server.py          29 public tools, health/metrics routes, bounded dispatch
internal_app.py            Restricted 21-tool internal MCP
research_cli.py            Codex login and authentication-readiness helper
core/
  http_security.py         Bearer identities and HTTP admission limits
  research_service.py      Queue, worker lock, cancellation and job deadline
  research_store.py        SQLite jobs, reports and progress events
  research_workflow.py     Role ordering, schemas and report validation
  research_runtime.py      Codex SDK configuration, turn limits and execution trace
  research_tools.py        Internal tool allowlist
  data_loader.py           Historical market-data retrieval
  indicator_registry.py    Curated indicator groups
  quant_settings.py        Trading-year convention
  telemetry.py             Best-effort PostgreSQL instrumentation
tools/                     Market, indicator, backtest and portfolio implementations
tests/                     Unit, integration and regression coverage
docs/                      Setup, API, architecture and operational guidance
```

The implementation is a single-host research system. Distributed job scheduling, automatic crash resumption, independently attested claim provenance, guaranteed real-time exchange data and order execution are outside its current scope. Test outcomes document tested behavior; they do not remove these limitations.
