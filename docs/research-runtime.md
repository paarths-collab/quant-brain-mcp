# Personal Codex research runtime

Claude calls the outer research MCP. Its background worker starts bounded Codex
specialist turns. Those turns use live web search and a separate internal MCP
allowlist; they cannot recursively start research jobs.

Install the optional runtime using Python 3.12:

```sh
python -m pip install -r requirements_research.txt
```

### Reuse your existing sign-in

To explicitly opt into reusing your existing Codex sign-in, set the profile in the terminal that will run the **outer server**, which starts the Codex workers:

```sh
export QUANT_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
```

Skip `login` when this profile is already signed in. The runtime overrides inherited MCP servers and plugins for its own subprocess; it does not edit your desktop configuration or copy credentials. Use the account check below after setting the internal MCP token. A command-only profile override is also available: `python research_cli.py check --codex-home ~/.codex`. That flag does not configure a subsequently started server, so retain the environment variable for server startup.

### Alternatively, create a dedicated profile

Leave `QUANT_CODEX_HOME` unset to use `~/.quant-brain/codex`, then run `python research_cli.py login`.
The explicit login command opens Codex's normal ChatGPT sign-in flow. For a
headless machine, use `python research_cli.py login --device-auth`. No login runs
when the server starts. Credentials stay in a dedicated Codex home, default
`~/.quant-brain/codex`; they are not copied from your desktop or included in
research prompts. Set `QUANT_CODEX_HOME` before login and server startup to choose
another directory. Login updates the selected profile's sign-in, so use `check` rather than `login` to verify an existing account.

Set `QUANT_INTERNAL_TOKEN` to the same secret used by the internal MCP server.
`QUANT_INTERNAL_MCP_URL` defaults to `http://127.0.0.1:8001/mcp`. Non-loopback
connections require HTTPS. Keep this server private. Then run:

```sh
python research_cli.py check
```

This checks account authentication only. It deliberately does **not** claim that
model access, web search or live tool calls have passed. Run a real research job
after both MCP interfaces are running to check those capabilities.

Optional settings:

- `QUANT_CODEX_MODEL`: model identifier available to your Codex account. Omit to use the runtime default.
- `QUANT_CODEX_ROLE_TIMEOUT`: per-role timeout in seconds; default 120, accepted range 1–600.

The pinned runtime disables shell execution, unified exec, apps, plugins,
computer/browser control and nested multi-agent spawning. It uses an empty
working directory, skips host skill discovery, suppresses project instructions,
and enforces a read-only sandbox with escalation denied. Only approved internal
calculation tools are configured. A cancelled or timed-out role closes its Codex
subprocess. These restrictions are defense in depth, not a reason to expose
private filesystem data to research agents.

A fresh isolated SDK startup and effective configuration were verified without
model access. Adapter tests cover lifecycle, cancellation, timeouts, secret-safe
errors and strict structured outputs. An authenticated quick research job has also completed through both HTTP MCP servers, with SDK-observed web search and successful private quote calls. This is an integration smoke test, not a research-quality benchmark. Standard/deep live runs and broader accuracy evaluation remain outstanding.

## Start both servers

Set these variables in both server terminals (use the same internal secret):

```sh
export QUANT_INTERNAL_TOKEN='<random secret of at least 32 characters>'
export QUANT_RESEARCH_ENABLED=true
```

Configure the outer server's `MCP_API_KEYS` as documented in [deployment](deployment.md). It maps an owner ID to the SHA-256 digest of their bearer token. Keep the raw outer token in your Claude MCP client configuration.

Run each command in its own terminal, using the installed Python environment:

```sh
python -m uvicorn internal_app:app --host 127.0.0.1 --port 8001 --workers 1
```

```sh
python -m uvicorn render_app:app --host 127.0.0.1 --port 8000 --workers 1
```

Connect Claude to `http://127.0.0.1:8000/mcp` using an HTTP MCP client that supports bearer authentication. A remote Claude client cannot reach your computer's loopback address; use a supported local bridge or an authenticated HTTPS deployment in that case. The internal server must remain private. Use one outer server worker because it owns the local research queue.

Ask Claude to call `start_research` with `question`, one to five `tickers` (for example `["TCS.NS"]`), and `depth` (`quick`, `standard`, or `deep`). It returns a job ID immediately. Poll `get_research_status`, then fetch `get_research_report` when completed. `cancel_research` stops an unwanted job. Jobs and reports are isolated by authenticated owner and persisted in SQLite. Set `QUANT_RESEARCH_DB` to choose the database location.

Quick research uses company and quant analysts, an auditor, and a synthesizer. Standard adds a lead and skeptic, with at most one correction round. Deep allows two correction rounds. Specialist calls have timeouts, and the complete job has a fifteen-minute timeout. There is no automatic trading.

## What still needs validation

The test suite checks orchestration, schemas, citation references, owner isolation, cancellation, and HTTP polling with simulated model responses. It does not establish investment accuracy. Citations and auditor judgments are model-generated; schema validation does not prove a source was fetched or a claim is true. Free market data can be delayed or unavailable. Reports include runtime-owned execution traces (tool names and statuses, without arguments or response payloads). These establish that calls occurred, not that every claim is correct. Before relying on the product, run broader authenticated end-to-end jobs, compare calculations and claims against independent sources, and evaluate a fixed set of Indian-stock questions. Preserve source timestamps and unresolved disagreements in the final answer.
