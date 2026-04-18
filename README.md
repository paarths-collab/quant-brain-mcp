# mcp-quant-brain

`mcp-quant-brain` is a high-performance Model Context Protocol (MCP) server designed for Quant Analysts and Financial Engineers. It provides a robust suite of tools for financial data ingestion, technical analysis, and advanced portfolio optimization.

## Features

- **Multi-Market Support**: Seamlessly handle US (e.g., `AAPL`) and Indian (e.g., `RELIANCE.NS`) stock data.
- **Automated Currency Normalization**: Built-in USD/INR conversion for cross-market portfolio comparisons.
- **Deep Technical Analysis**: Exposure to over 150+ indicators via `pandas-ta`.
- **Advanced Portfolio Optimization**:
  - Mean-Variance Optimization (MVO)
  - Hierarchical Risk Parity (HRP)
  - Black-Litterman Model
- **Integrated Backtesting**: Realistic performance simulation using `vectorbt` with transaction cost considerations.
- **Dynamic Extensibility**: Automatically registers new tools and indicators placed in the `tools/` directory.

## Project Structure

```text
mcp-quant-brain/
├── core/                # Core logic (Data loading, Forex, Mapping)
├── tools/               # MCP Tool implementations
│   ├── backtesting/     # Strategy & Portfolio backtesting logic
│   ├── optimization/    # Mean-Variance and HRP optimizers
│   ├── indicators/      # Technical analysis wrappers
│   └── strategies/      # predefined trading logic
├── knowledge/           # Static data & Risk manifolds
├── main.py              # Entry point & FastMCP server definition
└── requirements.txt     # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.10+
- An internet connection (for fetching market data via `yfinance`)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mcp-quant-brain
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
  source .venv/Scripts/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 📖 How to Use

The server is built using the official `mcp-python-sdk`. Once running, it exposes several tools that can be called by any MCP-compatible client.

### Running the Server

To start the server locally:
```bash
python main.py
```

## Render Keepalive

If you deploy to Render free tier, the service can sleep when idle. This repo includes a GitHub Actions workflow that pings the Render health endpoint every 5 minutes to keep the instance warm.

Set this repository secret in GitHub:

- `RENDER_HEALTH_URL`: your Render health endpoint, for example `https://mcp-quant-brain.onrender.com/health`

The workflow file is [`.github/workflows/render-keepalive.yml`](.github/workflows/render-keepalive.yml).

You can also run it manually from the GitHub Actions tab using `workflow_dispatch`.

### Example Usage (with MCP Client)

#### 1. Generate an Optimized Portfolio Verdict
This is the "Ultimate Tool" that fetches data, optimizes weights between tickers (even across USD/INR markets), backtests the result, and provides a final verdict.

```json
// Tool: generate_optimized_verdict
{
  "tickers": ["AAPL", "RELIANCE.NS", "TSLA", "TCS.NS"],
  "amount": 50000
}
```

#### 2. Fetch Single Stock Data
```json
// Tool: fetch_data
{
  "ticker": "RELIANCE.NS"
}
```

#### 3. Compute Technical Indicators
Indicators are registered as `get_[indicator_name]` tools.
```json
// Tool: get_rsi
{
  "ticker": "AAPL"
}
```

## Verdict Logic

The server evaluates backtest results against a `VERDICT_LOGIC` manifest:
- **STRONG BUY**: Sharpe Ratio > 1.5, Win Rate > 60%, Max Drawdown < 15%.
- **STAY AWAY**: Negative returns or Sharpe Ratio < 0.3.
- **RISKY MOMENTUM**: High returns (>30%) but erratic drawdown (>25%).

## 🧪 Dependencies

- **mcp-python-sdk**: The official Model Context Protocol implementation.
- **yfinance**: Market data source.
- **PyPortfolioOpt**: Modern Portfolio Theory tools.
- **vectorbt**: Vectorized backtesting.
- **pandas-ta**: Technical Analysis library.

---
*Note: This tool is for informational purposes only. Trading involves risk.*
# quant-brain-mcp-
