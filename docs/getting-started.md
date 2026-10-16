# Getting Started

Hosted connections require an operator-issued bearer token. Use a client with custom Authorization-header support; this server does not provide an OAuth login flow. See [deployment configuration](deployment.md).

## Choose your endpoint

For a personal VPS, use your configured public URL, such as
`https://quant.example.com/mcp`, after completing the [VPS setup](vps-deployment.md).
Replace the Render URL in the examples below with that URL. The example domain
is a placeholder, not a deployed service.

The existing Render address is:

```text
https://mcp-quant-brain.onrender.com/mcp
```

Transport: **Streamable HTTP**.

Its deployed revision, authentication, and optional research configuration need
separate verification. The checked-in Render configuration installs the base
market server; it does not provision Codex research. `/mcp` is a protocol endpoint,
not a webpage or dashboard.

## Personal Codex research setup

For Claude → Quant Brain → Codex research agents on your computer, follow the
[research runtime guide](research-runtime.md#start-both-servers). It includes local
secret generation, two-server startup, and a Claude Code connection that stores an
environment-variable reference instead of your raw token. A deployed URL alone
does not enable the optional research workers or authenticate Codex.

## Claude Desktop / Claude Web

1. Open **Customize → Connectors → Add → Add custom connector**.
2. Enter the outer server's public HTTPS `/mcp` URL.
3. Choose **No sign in** for OAuth, since this server uses a fixed bearer token.
4. Under **Request headers**, set `Authorization` to `Bearer <operator-issued token>`.
5. Add the connector and enable it for the conversation.

The request originates from Anthropic's cloud, including in Desktop; `localhost`
URLs do not work as remote connectors. Local Desktop stdio servers are a separate
mechanism. [Official connector instructions](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

## Claude Code (CLI)

Load your operator-issued token into `QUANT_CLIENT_TOKEN` from a local secret
store, then use a literal variable reference:

```sh
claude mcp add-json --scope user quant-brain '{"type":"http","url":"https://mcp-quant-brain.onrender.com/mcp","headers":{"Authorization":"Bearer ${QUANT_CLIENT_TOKEN}"}}'
claude mcp list
claude
```

Keep the JSON single-quoted, and launch Claude with that environment variable set.
For the local research setup, use `http://127.0.0.1:8000/mcp` instead of the hosted
URL. Check `/mcp` inside Claude to confirm connection.
[Official Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

## Other MCP clients

An MCP streamable HTTP client with bearer-header support works — point it at the URL above. The server is also listed in the [official MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=quant-brain-mcp) as `io.github.paarths-collab/quant-brain-mcp`.

## First prompt to try

> *"What's RELIANCE trading at, and is it overbought? Check momentum and trend."*

Claude will call `get_quote`, `analyze_momentum`, and `analyze_trend` and synthesize the answer.

## Ticker format

| Market | Format | Examples |
|---|---|---|
| US | plain symbol | `AAPL`, `MSFT`, `NVDA` |
| India (NSE) | symbol + `.NS` | `RELIANCE.NS`, `TCS.NS` |
| India (BSE) | symbol + `.BO` | `RELIANCE.BO` |
| Indices | caret prefix | `^GSPC` (S&P 500), `^NSEI` (NIFTY 50) |

Market tools can try `.NS` automatically — `RELIANCE` resolves to `RELIANCE.NS` and is benchmarked against NIFTY, not the S&P.

## Troubleshooting

### First request times out / "connection lost"

A sleeping hosted service can take time to wake. Retry a transient timeout with bounded backoff and check deployment logs if it persists. Authentication errors need configuration changes rather than repeated retries. Check liveness anytime:

```bash
curl https://mcp-quant-brain.onrender.com/health
```

### "Missing session ID"

The server runs stateless HTTP. Reconnect the client and confirm the URL ends in `/mcp`.

### A ticker returns "No data found"

- Indian stocks need `.NS` (auto-tried) or `.BO` (not auto-tried).
- Symbols can change after corporate actions; verify the current exchange symbol.
- Yahoo occasionally rate-limits; retry after a few seconds.

## Data expectations

- **Quote freshness**: provider delay varies. `as_of` / `fetched_at` record retrieval, not trade time; `market_timestamp` is unknown when the provider does not supply it.
- **NSE/BSE quotes**: the tool discloses an approximate delay; actual price age is unknown without a provider observation timestamp.
- **History**: daily bars, selectable window from `1d` to `max` via the `period` parameter (default `2y`).
- **History adjustment**: historical analysis requests dividend/split-adjusted bars; this is distinct from quote snapshots.

Research jobs are NSE-only and normalize bare symbols to `.NS`; the broader market-tool formats above do not extend the research workflow to other exchanges.
