import numpy as np
import pandas as pd

class WalkForwardBacktest:

    def __init__(self, train_window=252*2, test_window=63):
        self.train_window = train_window # 2 Years
        self.test_window = test_window   # 1 Quarter

    def run(self, returns, optimizer_func):
        """
        returns: DataFrame of asset returns
        optimizer_func: Function that takes (train_data) returns optimal weights
        """
        try:
            if len(returns) < self.train_window + self.test_window:
                print("Not enough history for Walk-Forward Backtest")
                return {
                    "average_test_return": 0.0,
                    "std_test_return": 0.0,
                    "walk_forward_returns": []
                }

            results = []

            # Rolling window
            for start in range(0, len(returns) - self.train_window - self.test_window, self.test_window):

                train = returns.iloc[start:start+self.train_window]
                test = returns.iloc[start+self.train_window : start+self.train_window+self.test_window]

                # Optimize on TRAIN data
                weights = optimizer_func(train)
                
                # Apply on TEST data
                # Dot product of test returns and weights
                test_portfolio_returns = (test * weights).sum(axis=1)
                
                # Cumulative return for this test period
                period_return = (1 + test_portfolio_returns).prod() - 1
                results.append(period_return)

            return {
                "average_test_return": float(np.mean(results)),
                "std_test_return": float(np.std(results)),
                "walk_forward_returns": results
            }
        except Exception as e:
            print(f"Walk-Forward Error: {e}")
            return {}
