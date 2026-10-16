# Personal Codex research runtime

Claude calls the outer research MCP. Its background worker starts bounded Codex
specialist turns. Those turns use live web search and a separate internal MCP
allowlist; they cannot recursively start research jobs.

This guide covers the current six-role NSE workflow. See the [agent and tool map](agents-and-tools.md)
for exact tools and permissions. To run it continuously on a remote host, follow
the [VPS deployment design](vps-deployment.md), including on-host login and persistent
services. The [global research roadmap](global-research-roadmap.md) describes future
browser access, additional specialists, and broader market research.

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
errors and strict structured outputs. Authenticated quick and deep research jobs have completed through both HTTP MCP servers, with SDK-observed web search and successful private quote calls. The deep run exercised all six roles and both correction rounds; its final result remained mixed with moderate confidence and excluded unaudited quote timestamps. These are integration checks, not an investment-accuracy benchmark. See [testing results](testing-results.md) for scope and remaining limitations.

## Start both servers

Create a local configuration file **outside the repository** once. This generates
separate client/internal secrets and stores only the client token's digest in the
server's authentication map. It reuses the Codex profile you already signed into.
The command refuses to overwrite an existing configuration:

```sh
python - <<'PYCONFIG'
import hashlib, json, os, secrets, shlex
from pathlib import Path

config = Path.home() / ".config" / "quant-brain" / "runtime.env"
config.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
client_token = secrets.token_urlsafe(32)
values = {
    "QUANT_CLIENT_TOKEN": client_token,
    "QUANT_INTERNAL_TOKEN": secrets.token_urlsafe(32),
    "QUANT_RESEARCH_ENABLED": "true",
    "QUANT_CODEX_HOME": os.environ.get("CODEX_HOME", str(Path.home() / ".codex")),
    "MCP_API_KEYS": json.dumps({"personal-research": hashlib.sha256(client_token.encode()).hexdigest()}),
}
fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as out:
    for key, value in values.items():
        out.write(f"export {key}={shlex.quote(value)}\n")
print("Local configuration created; no secrets printed.")
PYCONFIG
```

Do not commit this file or paste its contents into chat. For an existing deployment,
use its operator-issued client token and matching server digest instead; see
[deployment](deployment.md). Do not use a Codex sign-in token as an MCP bearer token.

Open two terminals in the repository, activate the Python environment where you
installed `requirements_research.txt`, and run:

**Terminal 1 — private calculation server**

```sh
source "$HOME/.config/quant-brain/runtime.env"
python -m uvicorn internal_app:app --host 127.0.0.1 --port 8001 --workers 1
```

**Terminal 2 — Claude-facing research server**

```sh
source "$HOME/.config/quant-brain/runtime.env"
python research_cli.py check
python -m uvicorn render_app:app --host 127.0.0.1 --port 8000 --workers 1
```

Keep both running. Use one outer server worker because it owns the local research
queue. The account check confirms sign-in, not a completed research run.

## Connect Claude Code locally

In a third terminal, with [Claude Code installed](https://code.claude.com/docs/en/setup),
load the local configuration and register the outer endpoint:

```sh
source "$HOME/.config/quant-brain/runtime.env"
claude mcp add-json --scope user quant-brain '{"type":"http","url":"http://127.0.0.1:8000/mcp","headers":{"Authorization":"Bearer ${QUANT_CLIENT_TOKEN}"}}'
claude mcp list
claude
```

Keep the JSON single-quoted: Claude stores the literal environment-variable
reference, not the bearer token. Start Claude from a terminal where
`QUANT_CLIENT_TOKEN` is set each time. In Claude, run `/mcp` and confirm
`quant-brain` is connected. If the name is already registered, inspect/update that
entry rather than creating duplicates. [Official Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

Try this prompt:

> Use Quant Brain to run quick research on TCS.NS. Check the latest available
> quote and company news, show source timestamps, and distinguish facts from
> assumptions. Poll the research job until it finishes, retrieve the report,
> then give your judgment with uncertainties and unresolved disagreements.

## Claude Desktop or claude.ai

The **remote connector** in Claude Desktop/web connects from Anthropic's cloud,
so it cannot reach `127.0.0.1` on your computer. For this personal local setup,
Claude Code above is the direct route. Desktop local stdio integrations are a
separate mechanism; this repository currently supplies authenticated HTTP
servers, not a configured Desktop stdio bridge.

For a remotely hosted instance, expose **only the outer server** over authenticated
HTTPS, then use **Customize → Connectors → Add → Add custom connector**. Enter the
outer `/mcp` URL. This server uses a fixed bearer credential, so choose **No sign in**
for OAuth and add a **Request headers** entry named `Authorization` with value
`Bearer <operator-issued outer token>`. That UI choice does not disable server
authentication. Enable the connector in your conversation. Do not assume the
existing hosted URL has the optional research runtime or Codex sign-in configured.
Keep the internal endpoint private and credentials on the server.
[Official custom connector documentation](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

## Research jobs

Ask Claude to call `start_research` with `question`, one to five `tickers` (for example `["TCS.NS"]`), and `depth` (`quick`, `standard`, or `deep`). It returns a job ID immediately. Poll `get_research_status`, then fetch `get_research_report` when completed. `cancel_research` stops an unwanted job. Jobs and reports are isolated by authenticated owner and persisted in SQLite. Set `QUANT_RESEARCH_DB` to choose the database location.

Quick research uses company and quant analysts, an auditor, and a synthesizer. Standard adds a lead and skeptic, with at most one correction round. Deep allows two correction rounds. Specialist calls have timeouts, and the complete job has a fifteen-minute timeout. There is no automatic trading.

## What still needs validation

The test suite checks orchestration, schemas, citation references, owner isolation, cancellation, and HTTP polling with simulated model responses. It does not establish investment accuracy. Citations and auditor judgments are model-generated; schema validation does not prove a source was fetched or a claim is true. Free market data can be delayed or unavailable. Reports include runtime-owned execution traces (tool names and statuses, without arguments or response payloads). These establish that calls occurred, not that every claim is correct. Before relying on the product, run broader authenticated end-to-end jobs, compare calculations and claims against independent sources, and evaluate a fixed set of Indian-stock questions. Preserve source timestamps and unresolved disagreements in the final answer.


## Source and execution quality

Reports now include `execution_status` and `source_retrievals`. The server attempts bounded retrieval of allowlisted official HTML and PDF sources before the auditor reviews them. Records distinguish extracted source text from model-authored excerpts; failures, missing dates and truncation stay visible. A completed job with failed MCP calls is `partial_failure`, not an all-pass result. Failed calls or failed cited retrievals lower confidence and prevent a supported outcome. A source site may still deny automated retrieval; this is reported rather than bypassed or presented as verified evidence.

The private MCP admits four calculation requests plus four independent GET streams, with eight bounded waiting slots for calculation bursts. Public admission limits remain unchanged. See [architecture](architecture.md#evidence-and-report-contract) for the exact retrieval scope and limits.
