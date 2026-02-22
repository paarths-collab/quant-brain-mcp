import numpy as np

class BayesianMonteCarlo:

    def __init__(self, simulations=1000, days=252):
        self.simulations = simulations
        self.days = days

    def simulate(self, returns):
        try:
            if returns.empty:
                 return {
                    "expected_return": 0.0,
                    "worst_case_5pct": 0.0
                }

            mu_hat = returns.mean()
            sigma_hat = returns.std()

            paths = []
            final_values = []

            for _ in range(self.simulations):
                # Sample parameters from distribution (Bayesian posterior-like)
                # Standard error of mean = sigma / sqrt(n)
                mu_sample = np.random.normal(mu_hat, sigma_hat/np.sqrt(len(returns)))
                
                # Sample sigma (simplified)
                sigma_sample = abs(np.random.normal(sigma_hat, sigma_hat*0.1))

                path = np.random.normal(mu_sample, sigma_sample, self.days)
                
                path_cumulative = np.cumprod(1 + path) - 1
                paths.append(path_cumulative)
                
                final_val = path_cumulative[-1]
                final_values.append(final_val)

            return {
                "expected": float(np.mean(final_values)),
                "worst_5pct": float(np.percentile(final_values, 5)),
                "paths": paths[:100]
            }
        except Exception as e:
            print(f"❌ Bayesian MC Error: {e}")
            return {
                "expected": 0.0,
                "worst_5pct": 0.0
            }
