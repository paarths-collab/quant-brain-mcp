import numpy as np

class BlackLitterman:

    def __init__(self, tau=0.05):
        self.tau = tau

    def optimize(self, returns, market_weights, views, view_confidence):
        """
        returns: DataFrame of historical returns
        market_weights: array of benchmark/market cap weights
        views: list of views (Q)
        view_confidence: list of confidences (diagonal of Omega, or just list)
        """
        try:
            cov = returns.cov() * 252
            
            # Implied Equilibrium Returns (Pi) using Market Weights (Reverse Optimization)
            # Assuming risk aversion delta = 2.5 (standard)
            delta = 2.5 
            pi = delta * cov @ market_weights

            # Simple view matrix P (Identity for absolute views on assets)
            # Improving this slightly to match user's structure: user provided Q and Confidence.
            # Assuming P is Identity for simplicity (1-to-1 view on each asset).
            
            # Just take the first N views if mismatched
            num_assets = len(market_weights)
            
            # If views provided are less than assets, assume neutral on others (0 view)
            # Or simplified: User likely meant "views" as the expected return vector Q
            Q = np.array(views) # Vector of expected returns
            
            # Construct P as identity
            P = np.eye(len(Q)) 
            
            # Construct Omega (Confidence Matrix)
            # User provided "view_confidence" - likely variance/uncertainty of view? 
            # Or confidence 0-1? 
            # Standard BL: Omega is the uncertainty variance. 
            # If standard deviation provided, square it.
            # Assuming input is variance or uncertainty metric.
            omega = np.diag(view_confidence)

            # Heuristic: Match dimensions
            if len(Q) != num_assets:
                 # Resize or fallback
                 return market_weights # Fallback

            # BL Formula
            inv_tau_cov = np.linalg.inv(self.tau * cov)
            inv_omega = np.linalg.inv(omega)
            
            # Posterior Mean (Combined Return Vector)
            middle_term = np.linalg.inv(inv_tau_cov + P.T @ inv_omega @ P)
            mu_bl = middle_term @ (inv_tau_cov @ pi + P.T @ inv_omega @ Q)

            # Optimization (Max Sharpe using BL Expected Returns)
            # w = inv(Sigma) * mu_bl
            inv_cov = np.linalg.inv(cov)
            weights = inv_cov @ mu_bl
            weights /= np.sum(weights)

            return weights.tolist()
            
        except Exception as e:
            print(f"❌ Black-Litterman Error: {e}")
            return market_weights # Fallback to market weights
