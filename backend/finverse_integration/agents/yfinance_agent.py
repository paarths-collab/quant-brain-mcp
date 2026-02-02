# File: agents/yfinance_agent.py

import pandas as pd
import logging
from typing import Dict, Any
from backend.services.data_loader import get_history, get_company_snapshot, add_technical_indicators

logger = logging.getLogger(__name__)

class YFinanceAgent:
    """An agent for fetching and processing data from Yahoo Finance, now market-aware."""

    def get_full_analysis(self, ticker: str, market: str) -> Dict[str, Any]:
        """Provides a comprehensive data package for a stock."""
        logger.info(f"YFinanceAgent: Running full analysis for {ticker} in market '{market}'")
        
        snapshot = get_company_snapshot(ticker, market)
        
        if "error" in snapshot:
            return {"error": f"Failed to get snapshot for {ticker}: {snapshot['error']}"}

        hist_df = get_history(ticker, start="2020-01-01", end=pd.Timestamp.now().strftime('%Y-%m-%d'), market=market)
        
        if hist_df.empty:
            return {"error": f"Failed to get historical data for {ticker}."}

        enriched_df = add_technical_indicators(hist_df)

        return {
            "snapshot": snapshot,
            "historical_data": enriched_df,
            "live_quote": {
                "c": snapshot.get("currentPrice") or snapshot.get("regularMarketPrice", 0),
                "pc": snapshot.get("previousClose", 0)
            }
        }

    def get_simple_history(self, ticker: str, start_date: str, end_date: str, market: str) -> pd.DataFrame:
        """Fetches simple historical data for backtesting."""
        logger.info(f"YFinanceAgent: Fetching simple history for {ticker} in market '{market}'")
        
        return get_history(ticker, start=start_date, end=end_date, market=market)