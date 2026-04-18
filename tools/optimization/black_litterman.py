import numpy as np
from pypfopt import BlackLittermanModel, expected_returns, risk_models


def run_bl_optimization(S, mu, views=None, view_confidences=None):
    """Black-Litterman optimization with neutral-view fallback.

    If no views are supplied, use prior means as neutral absolute views so the
    optimizer does not fail on missing Q.
    """
    if views:
        bl = BlackLittermanModel(S, pi=mu, absolute_views=views, omega=view_confidences)
    else:
        # Neutral fallback requested by user: Q from prior means, P as identity.
        Q = np.asarray(mu.values).reshape(-1, 1)
        P = np.eye(len(mu))
        try:
            bl = BlackLittermanModel(S, pi=mu, Q=Q, P=P)
        except TypeError:
            # Compatibility fallback for versions that prefer absolute_views dicts.
            fallback_views = {asset: float(mu.loc[asset]) for asset in mu.index}
            bl = BlackLittermanModel(S, pi=mu, absolute_views=fallback_views)

    weights = bl.bl_weights()
    return {
        "adjusted_weights": dict(weights),
        "posterior_returns": bl.bl_returns().to_dict(),
        "posterior_covariance": bl.bl_cov().to_dict(),
        "view_mode": "explicit" if views else "neutral_prior_fallback",
        "view_count": len(views) if views else len(mu),
    }


def run_black_litterman(S, prior_returns, views=None, view_confidences=None):
    """Compatibility wrapper for legacy call sites."""
    return run_bl_optimization(S, prior_returns, views=views, view_confidences=view_confidences)


def optimize(price_df, views=None, view_confidences=None):
    """Calculate Black-Litterman posterior moments and adjusted weights."""
    mu = expected_returns.mean_historical_return(price_df)
    S = risk_models.sample_cov(price_df)
    return run_bl_optimization(S, mu, views=views, view_confidences=view_confidences)
