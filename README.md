# 🚀 Bloomberg Financial Analysis Platform

<div align="center">

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

*A comprehensive AI-enhanced financial analysis and trading strategy backtesting platform*

</div>

## 📋 Table of Contents
- [🎯 Overview](#-overview)
- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [🛠️ Setup](#️-setup)
- [🚀 Usage](#-usage)
- [📊 Strategies](#-strategies)
- [🤖 AI Agents](#-ai-agents)
- [📈 Dashboard Preview](#-dashboard-preview)
- [🔧 Configuration](#-configuration)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## 🎯 Overview

Bloomberg is a state-of-the-art financial analysis platform that combines quantitative trading strategies, AI-powered insights, and comprehensive market analysis. Built with Streamlit, it provides investors and analysts with a complete toolkit for market research, strategy backtesting, and AI-driven investment planning.

The platform features a modular architecture with AI agents, multiple trading strategies, and professional-grade visualization tools that enable users to build and test algorithmic trading strategies efficiently.

## ✨ Key Features

### 📈 **Strategy Backtesting**
- **15+ Trading Strategies**: Including EMA/SMA crossovers, RSI, MACD, Breakout, Pairs Trading, and more
- **Performance Metrics**: Comprehensive risk-adjusted returns analysis with Sharpe, Sortino, and Calmar ratios
- **Visual Analysis**: Interactive charts with trade signals, equity curves, and strategy-specific indicators

### 🧠 **AI-Powered Analysis**
- **Multi-Agent System**: Coordinated AI agents for fundamentals, technicals, sentiment, and sector analysis
- **Deep Dive Analysis**: Multi-dimensional stock evaluation covering 8+ analysis dimensions
- **AI Investment Planning**: Personalized investment recommendations based on your financial profile

### 🌍 **Global Market Support**
- **US & Indian Markets**: Full support for both markets with appropriate currency symbols
- **Real-time Data**: Integration with Yahoo Finance and Finnhub for live market data
- **Market Overview**: High-level snapshot of global market health and economic indicators

### 💸 **Paper Trading Integration**
- **Live Portfolio Tracking**: Connect to Alpaca paper trading accounts
- **Risk Management**: Real-time portfolio risk metrics and analysis
- **Performance Monitoring**: Track your paper trading performance against benchmarks

### 🎯 **Advanced Analytics**
- **Risk Metrics**: Alpha, beta, volatility, Value at Risk (VaR), and maximum drawdown
- **Benchmark Comparisons**: Compare strategies against market indices (SPY, QQQ, NIFTY etc.)
- **Correlation Analysis**: Understand strategy relationships and portfolio diversification

## 🏗️ Architecture

```
├── app.py                    # Main Streamlit application
├── config.py                 # Configuration and API keys
├── requirements.txt          # Python dependencies
├── agents/                   # AI agent implementations
│   ├── orchestrator.py       # Central coordinator
│   ├── analyst_agent.py      # Fundamental analysis
│   ├── ...                   # Other specialized agents
├── pages/                    # Streamlit page components
│   ├── 1_📈_Market_Overview.py
│   ├── 2_🔬_Deep_Dive_Analysis.py
│   ├── 3_📊_Strategy_Backtester.py
│   ├── 4_💬_AI_Consultant.py
│   └── 5_💸_Paper_Trading.py
├── strategies/               # Trading strategy modules
│   ├── ema_crossover.py
│   ├── macd_strategy.py
│   ├── rsi_strategy.py
│   └── ...                   # 15+ additional strategies
├── utils/                    # Utility functions
│   ├── data_loader.py
│   ├── risk_metrics.py
│   ├── visualization.py
│   └── portfolio_engine.py
└── data/                     # Market data and universes
    ├── us_stocks.csv
    └── nifty500.csv
```

## 🛠️ Setup

### Prerequisites
- Python 3.8 or higher
- Pip package manager

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/Bloomberg.git
   cd Bloomberg
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up API keys in environment variables:**
   ```bash
   # Create a .env file in the root directory
   echo "FINNHUB_API_KEY=your_finnhub_api_key_here" > .env
   ```

5. **Run the application:**
   ```bash
   streamlit run app.py
   ```

### Required API Keys
- **Finnhub API Key**: For market data and economic indicators
- **OpenAI API Key (optional)**: For enhanced AI analysis
- **Alpaca API Key (optional)**: For paper trading functionality

## 🚀 Usage

### Getting Started
1. Launch the application with `streamlit run app.py`
2. Navigate through the sidebar to access different analysis modules
3. Start with the Market Overview to understand current market conditions
4. Try the Strategy Backtester with sample tickers like AAPL, MSFT, or TSLA

### Strategy Backtesting
1. Go to **📊 Strategy Backtester** in the sidebar
2. Select a strategy from the 15+ available options
3. Enter a ticker symbol and date range
4. Adjust strategy parameters if needed
5. Run the backtest and analyze performance metrics

### Deep Dive Analysis
1. Navigate to **🔬 Deep Dive Analysis**
2. Enter a stock ticker for comprehensive analysis
3. Review the multi-agent analysis including:
   - Fundamentals
   - Technical indicators
   - News sentiment
   - Insider activity
   - Sector performance
   - Risk factors

### AI Investment Planning
1. Access **💬 AI Consultant**
2. Provide your financial profile and investment goals
3. Receive personalized investment recommendations
4. Get a comprehensive investment plan

## 📊 Trading Strategies

The platform includes over 15 quantitative trading strategies:

### 📈 **Trend Following**
- **EMA Crossover**: Exponential moving average crossover strategy
- **SMA Crossover**: Simple moving average crossover strategy
- **MACD Strategy**: Momentum-based trend following

### 📉 **Mean Reversion**
- **RSI Strategies**: Overbought/oversold signals using Relative Strength Index
- **Bollinger Bands**: Volatility-based mean reversion
- **Support/Resistance**: Trading at key price levels

### ⚡ **Breakout & Momentum**
- **Breakout Strategy**: Price breakouts above resistance levels
- **Channel Trading**: Donchian channels for trend identification
- **Momentum Strategy**: Capturing momentum-driven moves

### 🔄 **Specialized Strategies**
- **Pairs Trading**: Relative price movements of correlated securities
- **Fibonacci Pullback**: Using Fibonacci retracement levels
- **Mean Reversion**: Statistical mean reversion approach

Each strategy includes detailed performance metrics and interactive visualizations.

## 🤖 AI Agents

The platform features a sophisticated multi-agent system:

### **Core Agents:**
- **Analyst Agent**: Fundamental analysis and financial metrics evaluation
- **Technical Agent**: Technical analysis with chart patterns and indicators
- **Sentiment Agent**: News sentiment and social media analysis
- **Insider Agent**: Insider trading activity monitoring
- **Sector Agent**: Sector and industry analysis
- **Macro Agent**: Economic indicators and market sentiment
- **Risk Agent**: Risk assessment and portfolio optimization
- **Execution Agent**: Paper trading and execution management

### **Orchestration:**
The **Orchestrator Agent** coordinates all specialized agents to provide comprehensive, multi-dimensional analysis of any stock or market condition.

## 📈 Dashboard Preview

The platform features several interactive dashboards:

### **Market Overview**
- Real-time market indices and economic indicators
- Global market sentiment analysis
- Economic calendar and events

### **Strategy Backtester**
- Interactive performance charts with trade signals
- Multiple performance metrics (Sharpe, Sortino, Calmar ratios)
- Benchmark comparison capabilities
- Strategy-specific visualizations

### **Deep Dive Analysis**
- 8+ dimensional analysis of individual stocks
- Professional charts with technical indicators
- Risk-factor analysis and fundamental metrics
- Historical performance and trend analysis

## 🔧 Configuration

The platform can be configured via `config.py`:

```python
# Strategy defaults
DEFAULT_START_DATE = "2020-01-01"
DEFAULT_INITIAL_CAPITAL = 100000

# Backtesting settings
COMMISSION_RATE = 0.002

# UI settings
UI_DECIMAL_PLACES = 2

# Supported currencies
CURRENCY_SYMBOLS = {
    "USD": "$",
    "INR": "₹",
}
```


**Bloomberg Financial Analysis Platform**
*Enhancing Investment Decisions with AI and Quantitative Analysis*

⭐ Star this repo if you find it helpful!

</div>
