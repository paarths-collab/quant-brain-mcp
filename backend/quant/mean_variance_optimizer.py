import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize

class MeanVarianceOptimizer:

    def __init__(self, tickers):
        self.tickers = tickers

    def fetch_data(self):
        if not self.tickers:
            return pd.DataFrame()
        # Using period="1y"
        data = yf.download(self.tickers, period="1y", progress=False)["Adj Close"]
        if isinstance(data, pd.Series):
             data = data.to_frame()
        returns = data.pct_change().dropna()
        return returns

    def optimize(self):
        try:
            returns = self.fetch_data()
            if returns.empty or returns.shape[1] < 2:
                 return {
                    "optimal_weights": {t: 1.0/len(self.tickers) for t in self.tickers} if self.tickers else {},
                    "expected_sharpe": 0.0,
                    "error": "Not enough data or assets for optimization"
                }

            mean_returns = returns.mean()
            cov_matrix = returns.cov()

            num_assets = len(self.tickers)

            def portfolio_performance(weights):
                portfolio_return = np.sum(mean_returns * weights) * 252
                portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix * 252, weights)))
                if portfolio_vol == 0:
                    return 0
                sharpe = portfolio_return / portfolio_vol
                return -sharpe  # maximize Sharpe

            constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
            bounds = tuple((0, 1) for _ in range(num_assets))
            init_guess = num_assets * [1. / num_assets]

            result = minimize(portfolio_performance, init_guess,
                              method='SLSQP',
                              bounds=bounds,
                              constraints=constraints)

            return {
                "optimal_weights": dict(zip(self.tickers, result.x)),
                "expected_sharpe": float(-result.fun)
            }
        except Exception as e:
             return {
                "optimal_weights": {},
                "expected_sharpe": 0.0,
                "error": str(e)
            }
