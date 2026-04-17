# Copilot Instructions for Stock Analysis Tools

This project includes a Model Context Protocol (MCP) server that provides advanced financial analysis tools. 

## When to use MCP Tools
- Use the `generate_optimized_verdict` tool whenever a user asks to optimize a portfolio, analyze multiple stocks together, or perform a backtest.
- Use the `get_<indicator>` tools (e.g., `get_rsi`, `get_macd`) for technical analysis of individual tickers.
- Use `fetch_data` to get raw OHLCV data.

## Tool-Specific Rules
### generate_optimized_verdict
- **Inputs**: List of tickers (e.g., `["AAPL", "RELIANCE.NS"]`), optional `amount`, and `optimize_type` ("mvo" or "hrp").
- **HRP**: Prefer Hierarchical Risk Parity (`hrp`) if the user mentions "low risk" or "risk parity".
- **Backtest**: This tool automatically performs a backtest and returns a Sharp Ratio and Verdict.

## Data Types
- Note that all outputs are serialized to standard JSON strings/numbers to avoid `int64` errors.
- If you encounter a serialization error, suggest the user restart their MCP server in VS Code.

## MCP-First Discipline
- For analysis and verdicts, always prefer registered MCP tools over local ad-hoc calculations.
- Do not run custom math snippets if an MCP tool already provides that calculation.
- If an MCP tool fails, clearly mark any local computation as a fallback and recommend rerunning after the MCP issue is resolved.
