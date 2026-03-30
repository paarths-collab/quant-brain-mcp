"""
Isolated trade_levels_service for chat/core.
Calculates support/resistance and risk levels for trade setup.
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional


class TradeLevelsService:
    """Calculate trade entry, target, and stop-loss levels."""

    def get_levels(self, ticker: str, risk_reward: float = 2.0) -> Dict[str, Any]:
        """
        Calculate trade levels using ATR-based stops and targets.
        """
        try:
            stock = yf.Ticker(ticker.upper())
            hist = stock.history(period="3mo")

            if hist.empty:
                return {"error": f"No data for {ticker}"}

            current_price = float(hist["Close"].iloc[-1])

            # ATR for stop calculation
            atr_period = 14
            high_low = hist["High"] - hist["Low"]
            high_close = (hist["High"] - hist["Close"].shift()).abs()
            low_close = (hist["Low"] - hist["Close"].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = float(tr.rolling(atr_period).mean().iloc[-1])

            stop_loss = current_price - (1.5 * atr)
            target = current_price + (risk_reward * 1.5 * atr)

            # Support / Resistance from recent pivot highs/lows
            recent = hist.tail(30)
            support = float(recent["Low"].min())
            resistance = float(recent["High"].max())

            return {
                "ticker": ticker.upper(),
                "current_price": round(current_price, 2),
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "support": round(support, 2),
                "resistance": round(resistance, 2),
                "atr": round(atr, 2),
                "risk_reward": risk_reward,
            }
        except Exception as e:
            return {"ticker": ticker, "error": str(e)}

    def calculate_risk(self, entry: float, stop: float, target: float, capital: float = 100000) -> Dict[str, Any]:
        """Calculate risk/reward metrics for a given trade setup."""
        risk = abs(entry - stop)
        reward = abs(target - entry)
        rr = reward / risk if risk > 0 else 0
        position_size = (capital * 0.02) / risk if risk > 0 else 0
        return {
            "risk_per_share": round(risk, 2),
            "reward_per_share": round(reward, 2),
            "risk_reward_ratio": round(rr, 2),
            "position_size": round(position_size),
            "total_risk": round(position_size * risk, 2),
        }
