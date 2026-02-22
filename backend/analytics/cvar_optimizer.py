import numpy as np

class CVaROptimizer:

    def optimize(self, returns, alpha=0.05):
        try:
            if returns.empty:
                return []

            portfolio_returns = returns.values
            num_assets = returns.shape[1]
            
            mean_returns = portfolio_returns.mean(axis=0)

            best_weights = np.ones(num_assets) / num_assets
            best_cvar = -float("inf") # Maximize "negative loss" -> Minimize loss

            # Monte Carlo Optimization (Sampling weights)
            for _ in range(5000):
                weights = np.random.random(num_assets)
                weights /= weights.sum()

                port = portfolio_returns @ weights

                # Value at Risk (VaR)
                var = np.percentile(port, alpha*100)
                
                # CVaR is mean of returns strictly below VaR
                tail_losses = port[port <= var]
                if len(tail_losses) == 0:
                    cvar = var
                else:
                    cvar = tail_losses.mean()

                # Typically CVaR is a negative return number (loss). 
                # We want to maximize this (make it closest to 0 or positive)
                if cvar > best_cvar:
                    best_cvar = cvar
                    best_weights = weights

            return best_weights.tolist()
            
        except Exception as e:
            print(f"❌ CVaR Error: {e}")
            return []
