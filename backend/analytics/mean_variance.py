import yfinance as yf
import numpy as np

class MeanVarianceOptimizer:

    def __init__(self, lookback_years=3):
        self.lookback_years = lookback_years

    def optimize(self, tickers):
        if not tickers:
            return {}

        try:
            data = yf.download(
                tickers,
                period=f"{self.lookback_years}y",
                interval="1d",
                auto_adjust=True,
                progress=False
            )["Close"]

            # Handle single ticker case
            if len(tickers) == 1:
                return {
                    "tickers": tickers,
                    "weights": [1.0],
                    "expected_return": 0.0, # Not useful for single stock
                    "volatility": 0.0
                }

            returns = data.pct_change().dropna()
            
            if returns.empty:
                 return {
                    "tickers": tickers,
                    "weights": [1.0/len(tickers)] * len(tickers),
                    "expected_return": 0.0, 
                    "volatility": 0.0
                }

            mean_returns = returns.mean() * 252
            cov_matrix = returns.cov() * 252

            # Basic Max Sharpe (Tangency Portfolio)
            # Analytical: w = inv(Sigma) * mu / sum(inv(Sigma) * mu)
            # Note: This allows short selling (negative weights). 
            # For strict robust usage, we might clip negative weights or use a solver.
            # But adhering to the user's "clean" implementation:

            try:
                inv_cov = np.linalg.inv(cov_matrix)
                weights = inv_cov @ mean_returns
                weight_sum = np.sum(weights)
                
                if weight_sum == 0:
                     weights = np.ones(len(tickers)) / len(tickers)
                else:
                    weights /= weight_sum
            except np.linalg.LinAlgError:
                # Fallback to equal weights if singular matrix
                weights = np.ones(len(tickers)) / len(tickers)

            port_return = weights @ mean_returns
            port_vol = np.sqrt(weights @ cov_matrix @ weights)

            return {
                "tickers": tickers,
                "weights": weights.tolist(),
                "expected_return": float(port_return),
                "volatility": float(port_vol)
            }
        except Exception as e:
            print(f"❌ MVO Error: {e}")
            return {}
