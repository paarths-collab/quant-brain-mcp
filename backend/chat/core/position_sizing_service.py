"""
Isolated position_sizing_service for chat/core.
Provides Kelly Criterion and fixed-fraction position sizing.
"""
from typing import Dict, Any, Optional


class PositionSizingService:
    """Calculate optimal position sizes using various methods."""

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        capital: float = 100000,
    ) -> Dict[str, Any]:
        """
        Kelly Criterion position sizing.
        f* = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
        """
        try:
            if avg_win <= 0 or avg_loss <= 0:
                return {"error": "avg_win and avg_loss must be positive"}

            loss_rate = 1 - win_rate
            w = avg_win / avg_loss  # win/loss ratio
            f = win_rate - (loss_rate / w)
            f = max(0, min(f, 0.25))  # Cap at 25% of capital

            position_size = capital * f
            return {
                "method": "kelly",
                "fraction": round(f, 4),
                "position_size": round(position_size, 2),
                "capital": capital,
                "win_rate": win_rate,
            }
        except Exception as e:
            return {"error": str(e)}

    def fixed_fraction(
        self,
        risk_pct: float = 0.02,
        capital: float = 100000,
        stop_loss_pct: float = 0.05,
    ) -> Dict[str, Any]:
        """Fixed-fraction position sizing based on risk percentage."""
        try:
            risk_amount = capital * risk_pct
            position_size = risk_amount / stop_loss_pct if stop_loss_pct > 0 else 0
            return {
                "method": "fixed_fraction",
                "risk_pct": risk_pct,
                "risk_amount": round(risk_amount, 2),
                "position_size": round(position_size, 2),
                "capital": capital,
            }
        except Exception as e:
            return {"error": str(e)}

    def calculate(self, method: str = "kelly", **kwargs) -> Dict[str, Any]:
        if method == "kelly":
            return self.kelly_criterion(**kwargs)
        return self.fixed_fraction(**kwargs)
