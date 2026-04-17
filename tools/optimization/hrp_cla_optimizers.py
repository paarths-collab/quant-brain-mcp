from pypfopt import HRPOpt, CLA


def run_alternative_optimizers(returns_df, method="hrp"):
    """
    STRATEGY: Diversification without relying on 'Expected Returns'.
    WHEN TO USE:
        - 'HRP': BEST when market direction is unknown. It clusters stocks by correlation.
        - 'CLA': Use when there are strict upper/lower bound requirements.
    MARKET CONDITION: Chaotic or sideways markets.
    """
    if method == "hrp":
        hrp = HRPOpt(returns_df)
        weights = hrp.optimize()
    else:
        cla = CLA(returns_df.mean(), returns_df.cov())
        weights = cla.max_sharpe()

    return {"weights": dict(weights), "method": method.upper()}
