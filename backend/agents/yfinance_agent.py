# # File: agents/yfinance_agent.py


# File: agents/yfinance_agent.py

import logging
from typing import Dict, Any
import pandas as pd

from backend.services.data_loader import get_history, get_company_snapshot

logger = logging.getLogger(__name__)


class YFinanceAgent:
    """
    Market Data Agent (Yahoo Finance)

    Responsibilities:
    - Fetch raw company snapshot
    - Fetch raw historical OHLC data
    - Be market-aware (US / India etc.)

    Non-responsibilities:
    - NO technical indicators
    - NO valuation / analysis
    - NO sentiment
    - NO opinions
    """

    def get_market_data(
        self,
        ticker: str,
        market: str,
        start_date: str = "2020-01-01",
        end_date: str | None = None,
    ) -> Dict[str, Any]:
        """
        Fetches normalized raw market data for a stock.
        """
        logger.info(
            f"YFinanceAgent: Fetching market data for {ticker} (market={market})"
        )

        if end_date is None:
            end_date = pd.Timestamp.now().strftime("%Y-%m-%d")

        # --- Company Snapshot ---
        snapshot = get_company_snapshot(ticker, market)
        if not isinstance(snapshot, dict) or "error" in snapshot:
            return {
                "error": f"Failed to fetch company snapshot for {ticker}",
                "details": snapshot,
            }

        # --- Historical OHLC Data ---
        history_df = get_history(
            ticker=ticker,
            start=start_date,
            end=end_date,
            market=market,
        )

        if history_df is None or history_df.empty:
            return {
                "error": f"No historical data available for {ticker}",
            }

        return {
            "ticker": ticker,
            "market": market,
            "snapshot": snapshot,
            "historical_data": history_df,
        }

    def get_price_history(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        market: str,
    ) -> pd.DataFrame:
        """
        Lightweight price history fetcher.
        Intended for:
        - Backtesting
        - Portfolio engine
        - Strategy simulations
        """
        logger.info(
            f"YFinanceAgent: Fetching price history for {ticker} "
            f"(market={market}, {start_date} → {end_date})"
        )

        return get_history(
            ticker=ticker,
            start=start_date,
            end=end_date,
            market=market,
        )

    def get_full_analysis(self, ticker: str, market: str) -> Dict[str, Any]:
        """Provides a comprehensive data package for a stock."""
        logger.info(f"YFinanceAgent: Running full analysis for {ticker} in market '{market}'")
        
        # Use existing get_market_data for consistency
        market_data = self.get_market_data(ticker, market)
        
        if "error" in market_data:
            return market_data
            
        snapshot = market_data.get("snapshot", {})
        hist_df = market_data.get("historical_data")
        
        if hist_df is None or hist_df.empty:
             return {"error": f"Failed to get historical data for {ticker}."}

        # Calculate simple technicals if not present (or rely on what get_market_data returns)
        # For now, return the structure expected by consumers of get_full_analysis
        
        return {
            "snapshot": snapshot,
            "historical_data": hist_df,
            "live_quote": {
                "c": snapshot.get("currentPrice") or snapshot.get("regularMarketPrice", 0),
                "pc": snapshot.get("previousClose") or snapshot.get("regularMarketPreviousClose", 0)
            }
        }