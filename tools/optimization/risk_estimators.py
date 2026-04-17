from pypfopt import risk_models


def get_risk_matrix(price_df, method="ledoit_wolf"):
    """
    STRATEGY: Measuring how assets move together (correlation).
    WHEN TO USE:
        - 'sample_cov': Use when you have >5 years of clean data.
        - 'ledoit_wolf': BEST for Indian stocks or portfolios with many tickers.
          It 'shrinks' extreme outliers to make the model more stable.
        - 'exp_cov': Use if you expect recent high volatility to continue.
    """
    if method == "sample":
        return risk_models.sample_cov(price_df)
    elif method == "exp_cov":
        return risk_models.exp_cov(price_df)
    return risk_models.CovarianceShrinkage(price_df).ledoit_wolf()
