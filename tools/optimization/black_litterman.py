import numpy as np
from pypfopt import BlackLittermanModel, expected_returns, risk_models
from pypfopt.black_litterman import market_implied_prior_returns

# Conventional equity risk-aversion coefficient (He & Litterman).
DEFAULT_RISK_AVERSION = 2.5


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


def optimize(price_df, views=None, view_confidences=None, risk_aversion=DEFAULT_RISK_AVERSION):
    """Black-Litterman posterior from an equilibrium prior plus views.

    The prior is the return vector implied by an equal-weight market portfolio
    (pi = delta * S * w_eq); per-asset market caps are not available offline.
    Without explicit views, each asset's historical mean return is an absolute
    view with PyPortfolioOpt's default uncertainty (omega proportional to
    tau * P S P'), so the posterior shrinks noisy historical means toward
    equilibrium instead of anchoring on them.
    """
    S = risk_models.sample_cov(price_df)
    equal_caps = {asset: 1.0 for asset in price_df.columns}
    prior = market_implied_prior_returns(equal_caps, risk_aversion, S)
    view_source = "explicit"
    if not views:
        views = expected_returns.mean_historical_return(price_df).to_dict()
        view_source = "historical_mean_returns"
    bl = BlackLittermanModel(S, pi=prior, absolute_views=views, omega=view_confidences,
                             risk_aversion=risk_aversion)
    return {
        "adjusted_weights": dict(bl.bl_weights()),
        "posterior_returns": bl.bl_returns().to_dict(),
        "posterior_covariance": bl.bl_cov().to_dict(),
        "prior": "equal_weight_equilibrium",
        "prior_returns": prior.to_dict(),
        "risk_aversion": risk_aversion,
        "view_mode": view_source,
        "view_count": len(views),
    }
