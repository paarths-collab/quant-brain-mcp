from pypfopt import EfficientFrontier, risk_models, expected_returns


def optimize(price_df):
    """Calculates weights using mean-variance optimization."""
    mu = expected_returns.mean_historical_return(price_df)
    S = risk_models.sample_cov(price_df)
    ef = EfficientFrontier(mu, S)
    weights = ef.max_sharpe()
    cleaned = ef.clean_weights()
    return {"optimized_weights": dict(cleaned)}
