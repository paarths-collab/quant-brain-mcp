"""
Isolated monte_carlo_service for chat/core.
Provides Monte Carlo simulation for portfolio projections.
"""
import numpy as np
import yfinance as yf
from typing import Dict, Any


class MonteCarloService:
    """Run Monte Carlo simulations on a ticker."""

    def simulate(
        self,
        ticker: str,
        days: int = 252,
        simulations: int = 500,
        initial_capital: float = 100000.0,
    ) -> Dict[str, Any]:
        try:
            stock = yf.Ticker(ticker.upper())
            hist = stock.history(period="1y")
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
