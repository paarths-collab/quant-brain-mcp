"""
Long-Term Investment Strategy Orchestrator

Responsibilities:
- Load market data
- Fetch fundamentals when needed
- Delegate logic to pure strategy modules
"""

from typing import Dict, Any
import pandas as pd
import yfinance as yf

from backend.services.data_loader import get_history

from backend.long_term.dca import run_dca
from backend.long_term.dividend import analyze_dividends
from backend.long_term.growth import analyze_growth
from backend.long_term.value import analyze_value
from backend.long_term.index_etf import analyze_index_etf


# =========================================================
# DCA / SIP STRATEGY
# =========================================================

def run_long_term_dca(
    ticker: str,
    start_date: str,
    end_date: str,
    market: str,
    monthly_investment: float,
) -> Dict[str, Any]:
    """
    Orchestrates data loading + DCA strategy execution
    """

    df = get_history(ticker, start_date, end_date, market)

    if df.empty or "Close" not in df.columns:
        return {"error": "No historical data available"}

    monthly_prices = df["Close"].resample("MS").first()

    return run_dca(
        price_series=monthly_prices,
        monthly_investment=monthly_investment
    )


# =========================================================
# DIVIDEND STRATEGY
# =========================================================

def run_dividend_strategy(
    ticker: str,
    start: str,
    end: str,
    market: str,
) -> Dict[str, Any]:

    df = get_history(ticker, start, end, market)
    if df.empty:
        return {"error": "No historical data available"}

    stock = yf.Ticker(ticker)

    return analyze_dividends(
        dividends=stock.dividends,
        prices=df["Close"],
        payout_ratio=stock.info.get("payoutRatio")
    )


# =========================================================
# GROWTH STRATEGY
# =========================================================

def run_growth_strategy(
    ticker: str,
    start: str,
    end: str,
    market: str,
) -> Dict[str, Any]:

    df = get_history(ticker, start, end, market)
    if df.empty:
        return {"error": "No historical data available"}

    stock = yf.Ticker(ticker)
    info = stock.info

    return analyze_growth(
        financials=stock.financials,
        prices=df["Close"],
        revenue_growth_q=info.get("revenueGrowth"),
        earnings_growth_q=info.get("earningsGrowth"),
    )


# =========================================================
# VALUE STRATEGY
# =========================================================

def run_value_strategy(
    ticker: str,
    start: str,
    end: str,
    market: str,
) -> Dict[str, Any]:

    df = get_history(ticker, start, end, market)
    if df.empty:
        return {"error": "No historical data available"}

    stock = yf.Ticker(ticker)

    return analyze_value(
        prices=df["Close"],
        quarterly_financials=stock.quarterly_financials,
        quarterly_balance_sheet=stock.quarterly_balance_sheet,
        shares_outstanding=stock.info.get("sharesOutstanding"),
        current_metrics=stock.info
    )


# =========================================================
# INDEX / ETF STRATEGY
# =========================================================

def run_index_strategy(
    ticker: str,
    start: str,
    end: str,
    market: str,
) -> Dict[str, Any]:

    df = get_history(ticker, start, end, market)
    if df.empty:
        return {"error": "No historical data available"}

    return analyze_index_etf(
        prices=df["Close"],
        adjusted_prices=df.get("Adj Close", df["Close"])
    )


# =========================================================
# STRATEGY REGISTRY (IMPORTANT)
# =========================================================

LONG_TERM_STRATEGIES = {
    "dca": run_long_term_dca,
    "dividend": run_dividend_strategy,
    "growth": run_growth_strategy,
    "value": run_value_strategy,
    "index": run_index_strategy,
}


from backend.services.risk_profile_utils import get_active_strategies

# Redundant imports removed; using locally defined wrapper functions



STRATEGY_DISPATCHER = {
    "dca": run_long_term_dca,
    "dividend": run_dividend_strategy,
    "growth": run_growth_strategy,
    "value": run_value_strategy,
    "index": run_index_strategy,
}


def run_long_term_strategy(
    ticker: str,
    start: str,
    end: str,
    market: str,
    capital: float,
    risk_profile: str,
    monthly_investment: float = 1000
):
    """
    Executes long-term strategies based on selected risk profile
    """

    strategies = get_active_strategies(risk_profile)

    results = {}

    for strategy_name, weight in strategies.items():
        allocated_capital = capital * weight
        executor = STRATEGY_DISPATCHER[strategy_name]

        if strategy_name == "dca":
            results[strategy_name] = executor(
                ticker=ticker,
                start_date=start,
                end_date=end,
                market=market,
                monthly_investment=monthly_investment
            )
        else:
            results[strategy_name] = executor(
                ticker=ticker,
                start=start,
                end=end,
                market=market
            )

    return {
        "metadata": {
            "risk_profile": risk_profile,
            "capital": capital,
            "strategy_weights": strategies,
        },
        "results": results
    }
