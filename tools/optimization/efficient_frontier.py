from pypfopt import EfficientSemivariance, EfficientCVaR


def run_cvar_optimization(returns_df):
    """CVaR optimization using full return history.

    Tries the returns-only constructor first, then falls back to the
    (expected_returns, returns) signature for compatibility across
    PyPortfolioOpt versions.
    """
    try:
        ec = EfficientCVaR(returns_df)
    except TypeError:
        mu = returns_df.mean() * 252
        ec = EfficientCVaR(mu, returns_df)

    weights = ec.min_cvar()
    return dict(weights)


def run_advanced_frontier(returns_df, method="cvar"):
    """
    STRATEGY: Optimizing for the 'Worst Case Scenario'.
    WHEN TO USE:
        - 'Semivariance': When you only care about 'Downside' risk, not total volatility.
        - 'CVaR': When you want to minimize the expected loss on the worst 5% of days.
    MARKET CONDITION: High-risk, crash-prone regimes (common in mid-cap Indian stocks).
    """
    if method == "semivariance":
        mu = returns_df.mean() * 252
        es = EfficientSemivariance(mu, returns_df)
        es.min_semivariance()
        weights = es.clean_weights()
    else:
        weights = run_cvar_optimization(returns_df)

    return {"weights": dict(weights), "method": method}
