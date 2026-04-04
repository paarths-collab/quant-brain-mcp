"""
Central Market Data Loader — Refactored to use unified backend.services.
Eliminates redundant yfinance logic and ensures architectural consistency.
"""
import pandas as pd
from typing import Dict, Any, Optional
from backend.services.market_data import market_service

def format_ticker(ticker: str, market: str) -> str:
    """[DELEGATED] Normalize ticker using unified market_service."""
    return market_service.normalize_ticker(ticker, market)

def get_history(
    ticker: str,
    start: str,
    end: str,
    market: str,
    interval: str = "1d",
) -> pd.DataFrame:
    """[DELEGATED] Fetch history using unified market_service."""
    return market_service.get_history(ticker, start=start, end=end, interval=interval)

def get_ohlcv(
    ticker: str,
    start: str,
    end: str,
    market: str,
) -> pd.DataFrame:
    """[DELEGATED] Fetch OHLCV using unified market_service."""
    # Ensure standard OHLCV columns
    df = market_service.get_history(ticker, start=start, end=end)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if df.empty or not all(c in df.columns for c in required):
        return pd.DataFrame()
    return df[required]

def get_returns(
    ticker: str,
    start: str,
    end: str,
    market: str,
) -> pd.Series:
    """[DELEGATED] Calculate returns using unified market_service."""
    df = get_history(ticker, start, end, market)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    return df["Close"].pct_change().dropna()

def get_benchmark_returns(symbol: str, start: str, end: str) -> pd.Series:
    """[DELEGATED] Fetch benchmark returns using unified market_service."""
    # Note: market_service.get_history works for indices too
    df = market_service.get_history(symbol, start=start, end=end)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    return df["Close"].pct_change().dropna()

def get_company_snapshot(ticker: str, market: str) -> Dict[str, Any]:
    """[DELEGATED] Get fundamentals snapshot using unified market_service."""
    info = market_service.get_fundamentals(ticker)
    return {
        "symbol": ticker,
        "market": market,
        **info
    }

def get_comprehensive_stock_data(ticker: str, market: str) -> Dict[str, Any]:
    """[DELEGATED] Thin wrapper for comprehensive data."""
    # NOTE: Technical domain uses this for reports.
    # We delegate to the unified market_service.
    info = market_service.get_fundamentals(ticker)
    return {
        "symbol": ticker,
        "company_name": info.get("shortName") or info.get("longName", ticker),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        **info
    }

# Compatibility alias
get_data = get_ohlcv
