import numpy as np
import yfinance as yf

class MonteCarloService:

    def simulate(self, ticker, simulations=500, days=30):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            if df.empty:
                 return {
                    "expected_price": 0.0,
                    "worst_case": 0.0,
                    "best_case": 0.0,
                    "error": "No data found"
                }
            
            returns = df["Close"].pct_change().dropna()
            
            if returns.empty:
                 return {
                    "expected_price": 0.0,
                    "worst_case": 0.0,
                    "best_case": 0.0,
                    "error": "Not enough data"
                }

            last_price = df["Close"].iloc[-1]

            simulated_prices = []

            for _ in range(simulations):
                price = last_price
                # Random walk simulation
                # Using numpy vectorization for speed
                daily_returns = np.random.choice(returns, days)
                cumulative_return = np.prod(1 + daily_returns)
                price *= cumulative_return
                simulated_prices.append(price)

            # Return top 20 paths for visualization
            visualization_paths = [
                # Get a mix of paths: best, worst, and randoms
                # Actually, just random 20 is fine for a fan chart, 
                # but let's include min/max/mean specific paths if we tracked them.
                # For simplicity, just taking the first 20 simulations.
            ]
            
            # Simple list of lists
            paths_data = [p.tolist() if isinstance(p, np.ndarray) else p for p in simulated_prices[:20]]

            return {
                "expected_price": float(np.mean(simulated_prices)),
                "worst_case": float(np.percentile(simulated_prices, 5)),
                "best_case": float(np.percentile(simulated_prices, 95)),
                "simulation_paths": paths_data,  # ADDED
                "days": days
            }
        except Exception as e:
            return {
                "expected_price": 0.0,
                "worst_case": 0.0,
                "best_case": 0.0,
                "error": str(e)
            }
