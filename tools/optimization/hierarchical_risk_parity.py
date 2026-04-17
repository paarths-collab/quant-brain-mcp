from pypfopt import HRPOpt


def optimize(price_df):
    """Calculates weights using HRP."""
    returns = price_df.pct_change().dropna()
    hrp = HRPOpt(returns)
    weights = hrp.optimize()
    return {"optimized_weights": dict(weights)}
