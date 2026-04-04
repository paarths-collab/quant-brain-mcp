"""
Isolated monte_carlo_service for chat/core.
Refactored to use unified MarketDataService.
Ensures 100% architectural consistency and resolves direct yfinance usage.
"""
import numpy as np
from typing import Dict, Any
from backend.services.market_data import market_service

class MonteCarloService:
    """Run Monte Carlo simulations on a ticker."""

    def simulate(
        self,
        ticker: str,
        days: int = 252,
        simulations: int = 500,
        initial_capital: float = 100000.0,
    ) -> Dict[str, Any]:
        """
        [DELEGATED] Run Monte Carlo simulation using unified MarketDataService for history.
        """
        try:
            # MarketDataService handles normalization and safety
            # Period="1y" is handled by fetching 1 year of history
            hist = market_service.get_history(ticker, period="1y")
            
            if hist.empty or len(hist) < 10:
                return {"error": f"Insufficient data for {ticker}"}

            returns = hist["Close"].pct_change().dropna().values
            mu = float(np.mean(returns))
            sigma = float(np.std(returns))

            sim_returns = []
            for _ in range(simulations):
                daily = np.random.normal(mu, sigma, days)
                total = float((1 + daily).prod() - 1) * 100
                sim_returns.append(total)

            sim_arr = np.array(sim_returns)
            return {
                "ticker": ticker,
                "simulations": simulations,
                "days": days,
                "initial_capital": initial_capital,
                "percentiles": {
                    "p5": round(float(np.percentile(sim_arr, 5)), 2),
                    "p25": round(float(np.percentile(sim_arr, 25)), 2),
                    "p50": round(float(np.percentile(sim_arr, 50)), 2),
                    "p75": round(float(np.percentile(sim_arr, 75)), 2),
                    "p95": round(float(np.percentile(sim_arr, 95)), 2),
                },
                "risk": {
                    "var95": round(float(np.percentile(sim_arr, 5)), 2),
                    "ruin_probability": round(float((sim_arr < -50).mean() * 100), 2),
                },
            }
        except Exception as e:
            return {"ticker": ticker, "error": str(e)}
