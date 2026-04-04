"""
Shared data_loader pattern — Refactored to use unified backend.services.
Eliminates redundant yfinance logic and ensures architectural consistency.
"""
import pandas as pd
from typing import Optional
from backend.services.market_data import market_service

def get_history(
    ticker: str,
    start: str,
    end: str,
    market: str = "us",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    [DELEGATED] Fetch OHLCV history for a ticker using unified market_service.
    """
    try:
        # MarketDataService handles normalization and safety
        return market_service.get_history(ticker, start=start, end=end, interval=interval)
    except Exception as e:
        print(f"[data_loader] get_history({ticker}) failed: {e}")
        return pd.DataFrame()

def format_ticker(ticker: str, market: str = "us") -> str:
    """[DELEGATED] Normalize ticker using unified market_service."""
    return market_service.normalize_ticker(ticker, market)
