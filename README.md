# mcp-quant-brain

MCP server for stock analysis, strategy backtesting, portfolio optimization, and chart generation.

This product is built for users who want to ask natural-language questions like:

- "Analyze Indian sectors and tell me the best sector by risk-adjusted score."
- "Backtest MACD on IREDA.NS and show charts."
- "Optimize a US-India portfolio and explain risk."

## Product Use Cases

- Sector rotation analysis: identify the best-performing sector for a user-defined timeframe (for example `6m` or `1yr`) using return, volatility, drawdown, momentum, and correlation.
- Portfolio construction: optimize allocations across US and India tickers using methods like MVO, HRP, max Sharpe, min volatility, CVaR, and semivariance.
- Strategy validation: run rule-based backtests (MACD, RSI mean reversion, SMA crossover, breakout) before making discretionary decisions.
- Chart-first review: generate chart packs for portfolio diagnostics, strategy behavior, and sector-level risk structure.
- Company context enrichment: combine technical outputs with company-profile metadata for better explainability.

## What You Get

- US and India ticker support (`AAPL`, `RELIANCE.NS`, etc.)
- 150+ technical indicators
- Strategy backtests (MACD, RSI mean reversion, SMA crossover, breakout)
- Portfolio optimization (MVO, HRP, max Sharpe, min volatility, Black-Litterman, CVaR, semivariance)
- Sector intelligence (returns, volatility, momentum, drawdown, correlation, best-sector selection)
- Chart pack generation with isolated chart configs and default chart-first layout

## Use the Hosted MCP URL

Use streamable HTTP transport and connect your MCP client to:

- `https://mcp-quant-brain.onrender.com/mcp`

Free-tier Render note:

- The server may take up to 1-2 minutes to spin up if it was sleeping.
- If the first request times out, wait and retry.

## Connect in Claude (Desktop or Web)

Use connectors to add this MCP product in Claude.

### Claude Desktop

1. Open Claude Desktop settings.
2. Go to Connectors or MCP integrations.
3. Add a new connector.
4. Choose Streamable HTTP transport.
5. Set the connector URL to `https://mcp-quant-brain.onrender.com/mcp`.
6. Save and connect.
7. When Claude asks for tool permissions, click **Accept All** so all analysis and chart tools are available.

### Claude Web

1. Open Claude in browser and go to settings.
2. Open Connectors.
3. Add a custom connector.
4. Select Streamable HTTP transport.
5. Use `https://mcp-quant-brain.onrender.com/mcp` as the connector URL.
6. Complete connection.
7. When prompted for tool permissions, click **Accept All**.

If your first connection attempt fails, wait up to 2 minutes and retry once (free-tier cold start).

## Core Tools You’ll Use

- `generate_optimized_verdict`
- `generate_chart_pack`
- `generate_charts`
- `plot_charts`
- `get_company_profile`
- `find_sector_stock_pipeline_tool`
- `analyze_sector_intelligence_tool`
- Indicator tools like `get_rsi`, `get_macd`, `get_adx`, `get_supertrend`
- Strategy tools like `backtest_macd_momentum`, `backtest_rsi_mean_reversion`

## Example Questions (NLP)

- "Analyze IREDA.NS over 1 year, run MACD momentum backtest, and show charts."
- "Compare IT, Bank, Auto, Metal, Pharma, Realty sectors by return, risk, drawdown, and momentum."
- "Give me the best Indian sector using risk-adjusted ranking and show sector correlation matrix."
- "Optimize AAPL, MSFT, NVDA, RELIANCE.NS with CVaR and summarize risk flags."

## Render Endpoints

- MCP endpoint: `https://mcp-quant-brain.onrender.com/mcp`
- Health endpoint: `https://mcp-quant-brain.onrender.com/health`

## Troubleshooting

### "Missing session ID"

The server is configured with stateless HTTP mode. If you still see this:

1. Reconnect MCP client.
2. Ensure URL is exactly `/mcp`.

### "MCP server connection lost" / 504 / timeout

Usually cold-start or proxy timeout on free tier:

1. Wait up to 2 minutes.
2. Retry once.
3. Check `/health`.

### Charts not visible

Use `generate_charts` or `plot_charts` for image-friendly responses.

## Notes

- This is not financial advice.
- Data quality depends on upstream sources (mainly Yahoo Finance via `yfinance`).
- Use proper ticker suffixes for Indian stocks (for example `.NS`).
