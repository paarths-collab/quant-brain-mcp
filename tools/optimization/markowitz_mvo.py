from pypfopt import EfficientFrontier, risk_models, expected_returns

from tools.optimization.mean_variance import max_sharpe_or_min_volatility


def optimize(price_df):
    """Calculates weights using mean-variance optimization."""
    mu = expected_returns.mean_historical_return(price_df)
    S = risk_models.sample_cov(price_df)
    ef, target, note = max_sharpe_or_min_volatility(lambda: EfficientFrontier(mu, S))
    cleaned = ef.clean_weights()
    return {"optimized_weights": dict(cleaned), "target_used": target, "fallback_note": note}
