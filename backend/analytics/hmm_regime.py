import numpy as np
try:
    from hmmlearn.hmm import GaussianHMM
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    print("⚠️ hmmlearn not installed. Regime detection disabled.")

class HMMRegimeDetector:

    def __init__(self, n_states=2):
        self.n_states = n_states
        if HMM_AVAILABLE:
            self.model = GaussianHMM(n_components=n_states, covariance_type="full", n_iter=100)
        else:
            self.model = None

    def fit_predict(self, returns):
        if not HMM_AVAILABLE or returns.empty:
            return []

        try:
            # Check for NaN/Inf
            clean_returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
            
            if clean_returns.empty:
                 return []

            # HMM expects column vector
            # Detect regime on MARKET (e.g. use mean of assets as proxy for "Market Regime")
            market_proxy = clean_returns.mean(axis=1).values.reshape(-1, 1)
            
            self.model.fit(market_proxy)
            hidden_states = self.model.predict(market_proxy)

            return hidden_states.tolist()
        except Exception as e:
            print(f"❌ HMM Error: {e}")
            return []
