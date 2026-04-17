from pypfopt import EfficientSemivariance, EfficientCVaR


def run_advanced_frontier(returns_df, method="cvar"):
    """
    STRATEGY: Optimizing for the 'Worst Case Scenario'.
    WHEN TO USE:
        - 'Semivariance': When you only care about 'Downside' risk, not total volatility.
        - 'CVaR': When you want to minimize the expected loss on the worst 5% of days.
    MARKET CONDITION: High-risk, crash-prone regimes (common in mid-cap Indian stocks).
    """
    if method == "semivariance":
        es = EfficientSemivariance(returns_df.mean(), returns_df.cov())
        es.min_semivariance()
        weights = es.clean_weights()
    else:
        ec = EfficientCVaR(returns_df)
        ec.min_cvar()
        weights = ec.clean_weights()

    return {"weights": dict(weights), "method": method}
