# Getting Started

Connect once, then everything is plain English. No API keys, no accounts, no local install.

## The URL

```text
https://mcp-quant-brain.onrender.com/mcp
```

Transport: **Streamable HTTP**.

## Claude Desktop

1. Open **Settings → Connectors** (or MCP integrations).
2. **Add custom connector**.
3. Transport: **Streamable HTTP**, URL as above.
4. Save and connect. Approve the tool permissions when prompted.

## Claude Web (claude.ai)

1. **Settings → Connectors → Add custom connector**.
2. Streamable HTTP, same URL.
3. Connect.

## Claude Code (CLI)

```bash
claude mcp add quant-brain --transport http https://mcp-quant-brain.onrender.com/mcp
```

## Other MCP clients

Any client that speaks MCP streamable HTTP works — point it at the URL above. The server is also listed in the [official MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=quant-brain-mcp) as `io.github.paarths-collab/quant-brain-mcp`.

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

Forgot the `.NS`? The server tries it automatically — `RELIANCE` resolves to `RELIANCE.NS` and is benchmarked against NIFTY, not the S&P.

## Troubleshooting

### First request times out / "connection lost"

The server runs on a free tier that sleeps after ~15 minutes idle and takes **~50 seconds** to wake. Wait a minute and retry — subsequent requests are fast. Check liveness anytime:

```bash
curl https://mcp-quant-brain.onrender.com/health
```

### "Missing session ID"

The server runs stateless HTTP. Reconnect the client and confirm the URL ends in `/mcp`.

### A ticker returns "No data found"

- Indian stocks need `.NS` (auto-tried) or `.BO` (not auto-tried).
- Some symbols change after corporate actions — e.g. Tata Motors' passenger-vehicle listing is now `TMPV.NS`.
- Yahoo occasionally rate-limits; retry after a few seconds.

## Data expectations (read once, trust forever)

- **US quotes**: near-real-time.
- **NSE/BSE quotes**: ~15 minutes delayed. Every quote response carries `as_of` and a delay note.
- **History**: daily bars, selectable window from `1d` to `max` via the `period` parameter (default `2y`).
- **Dividends**: included — prices are dividend/split-adjusted, so returns are total returns.
