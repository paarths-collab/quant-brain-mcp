import numpy as np


class MonteCarloSimulator:

    def __init__(self, simulations=1000, days=252):
        self.simulations = simulations
        self.days = days

    def simulate(self, daily_returns, days=None):

        if daily_returns.empty:
             return {
                "expected_return": 0.0,
                "worst_case_5pct": 0.0,
                "best_case_95pct": 0.0,
                "distribution": []
            }

        sim_days = days if days else self.days
        
        mean = daily_returns.mean()
        std = daily_returns.std()

        paths = []
        final_values = []
        
        for _ in range(self.simulations):
            simulated = np.random.normal(mean, std, sim_days)
            paths.append(simulated)
            
            cumulative = np.prod(1 + simulated)
            final_values.append(cumulative - 1)

        return {
            "expected_return": float(np.mean(final_values)),
            "worst_case_5pct": float(np.percentile(final_values, 5)),
            "best_case_95pct": float(np.percentile(final_values, 95)),
            "distribution": final_values,
            "paths": paths[:100]
        }
