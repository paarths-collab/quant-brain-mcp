from pypfopt import expected_returns


def get_expected_returns(price_df, method="capm"):
    """
    STRATEGY: Estimating the future growth of assets.
    WHEN TO USE:
        - 'mean': In stable, long-term trending markets.
        - 'ema': In fast-moving momentum markets (gives weight to recent price).
        - 'capm': BEST for diversified US/Indian portfolios as it uses market equilibrium.
    """
    if method == "mean":
        return expected_returns.mean_historical_return(price_df)
    elif method == "ema":
        return expected_returns.ema_historical_return(price_df)
    elif method == "capm":
        return expected_returns.capm_return(price_df)
    return expected_returns.mean_historical_return(price_df)
