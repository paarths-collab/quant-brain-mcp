from pypfopt import BlackLittermanModel


def run_black_litterman(S, prior_returns, views, view_confidences=None):
    """
    STRATEGY: The 'AI + Math' blend.
    WHEN TO USE: When the Agent has a specific 'View' on a stock.
    SITUATION: Blends market average (Prior) with the Agent's prediction (Views).
    """
    bl = BlackLittermanModel(S, pi=prior_returns, absolute_views=views, omega=view_confidences)
    weights = bl.bl_weights()
    return {
        "adjusted_weights": dict(weights),
        "view_count": len(views) if views else 0,
    }
from pypfopt import BlackLittermanModel, risk_models, expected_returns


def optimize(price_df, views=None, view_confidences=None):
    """Calculates weights using Black-Litterman."""
    mu = expected_returns.mean_historical_return(price_df)
    S = risk_models.sample_cov(price_df)
    bl = BlackLittermanModel(S, pi=mu, absolute_views=views, view_confidences=view_confidences)
    rets = bl.bl_returns()
    cov = bl.bl_cov()
    return {"posterior_returns": rets.to_dict(), "posterior_covariance": cov.to_dict()}
