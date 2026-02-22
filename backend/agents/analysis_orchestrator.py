"""
analysis_orchestrator.py

Composes stock analysis using lower-level agents.
NO direct UI formatting.
NO LLM.
NO ticker search logic.
"""

from typing import Dict, Any, Optional
from datetime import date, timedelta

import pandas as pd

from backend.agents.yfinance_agent import YFinanceAgent


class AnalysisOrchestrator:
    """
    High-level stock analysis orchestrator.

    Responsibilities:
    - Combine market data
    - Compute light performance & technical metrics
    - Return structured JSON for API / frontend
    """

    def __init__(self):
        self.market_agent = YFinanceAgent()

    def analyze_stock(
        self,
        ticker: str,
        market: Optional[str] = None,
    ) -> Dict[str, Any]:
        if market is None:
            market = "india" if ticker.isupper() and not ticker.endswith(".NS") else "us"

        market_data = self.market_agent.get_market_data(
            ticker=ticker,
            market=market,
            start_date="2020-01-01",
        )

        if "error" in market_data:
            return {
                "success": False,
                "ticker": ticker,
                "error": market_data["error"],
            }

        hist_df: pd.DataFrame = market_data["historical_data"]
        snapshot: Dict[str, Any] = market_data["snapshot"]

        # ---- Price & Performance ----
        close = hist_df["Close"]
        current_price = float(close.iloc[-1])
        prev_close = float(close.iloc[-2]) if len(close) > 1 else current_price

        daily_returns = close.pct_change().dropna()

        performance = {
            "current_price": current_price,
            "previous_close": prev_close,
            "change": current_price - prev_close,
            "change_percent": ((current_price - prev_close) / prev_close) * 100
            if prev_close else 0,
            "volatility_annualized": float(daily_returns.std() * (252 ** 0.5) * 100),
        }

        # ---- Moving Averages ----
        ma = {
            "sma_20": float(close.tail(20).mean()) if len(close) >= 20 else None,
            "sma_50": float(close.tail(50).mean()) if len(close) >= 50 else None,
            "sma_200": float(close.tail(200).mean()) if len(close) >= 200 else None,
        }

        # ---- Returns ----
        returns = {
            "1w": self._period_return(close, 5),
            "1m": self._period_return(close, 22),
            "1y": self._period_return(close, 252),
        }

        # ---- Technical Signals (LIGHT ONLY) ----
        signals = []
        if ma["sma_50"] and ma["sma_200"]:
            signals.append(
                "golden_cross"
                if ma["sma_50"] > ma["sma_200"]
                else "death_cross"
            )

        if ma["sma_50"]:
            signals.append(
                "price_above_50sma"
                if current_price > ma["sma_50"]
                else "price_below_50sma"
            )

        return {
            "success": True,
            "ticker": ticker,
            "market": market,
            "snapshot": {
                "name": snapshot.get("longName"),
                "sector": snapshot.get("sector"),
                "industry": snapshot.get("industry"),
                "market_cap": snapshot.get("marketCap"),
                "beta": snapshot.get("beta"),
                "pe_ratio": snapshot.get("trailingPE"),
            },
            "performance": performance,
            "returns": returns,
            "moving_averages": ma,
            "signals": signals,
        }

    @staticmethod
    def _period_return(close: pd.Series, periods: int) -> float:
        if len(close) <= periods:
            return 0.0
        return float(((close.iloc[-1] - close.iloc[-periods - 1]) /
                      close.iloc[-periods - 1]) * 100)



