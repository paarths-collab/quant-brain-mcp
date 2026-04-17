from pypfopt import EfficientFrontier, risk_models


def run_mvo_basic(mu, S, target="max_sharpe"):
    """
    STRATEGY: The Markowitz Efficient Frontier.
    WHEN TO USE: Standard asset allocation for a balanced portfolio.
    MARKET CONDITION: Bull markets (Max Sharpe) or Bear markets (Min Volatility).
    VERDICT: Tells the Agent the 'ideal' percentage of each stock.
    """
    S = risk_models.fix_nonpositive_semidefinite(S)
    ef = EfficientFrontier(mu, S)
    if target == "max_sharpe":
        ef.max_sharpe()
    else:
        ef.min_volatility()

    perf = ef.portfolio_performance()
    return {
        "weights": ef.clean_weights(),
        "expected_return": f"{perf[0]:.2%}",
        "volatility": f"{perf[1]:.2%}",
        "sharpe_ratio": round(perf[2], 2),
    }
