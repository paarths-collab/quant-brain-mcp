from pypfopt import EfficientFrontier, risk_models

MAX_SHARPE_FALLBACK_NOTE = (
    "No asset had a positive expected excess return in the training window, so the "
    "max-Sharpe portfolio is undefined; fell back to the minimum-volatility portfolio."
)


def max_sharpe_or_min_volatility(make_frontier):
    """Solve max-Sharpe, falling back to min-volatility when it is undefined.

    PyPortfolioOpt raises ValueError for max_sharpe when every expected return
    is at or below the risk-free rate -- routine for a declining training
    window. A fresh frontier is built for the fallback because the failed
    solve may leave objectives attached to the first one.
    Returns (frontier, target_used, note_or_None).
    """
    frontier = make_frontier()
    try:
        frontier.max_sharpe()
        return frontier, "max_sharpe", None
    except ValueError as exc:
        if "exceeding the risk-free rate" not in str(exc):
            raise
    frontier = make_frontier()
    frontier.min_volatility()
    return frontier, "min_volatility", MAX_SHARPE_FALLBACK_NOTE


def run_mvo_basic(mu, S, target="max_sharpe"):
    """
    STRATEGY: The Markowitz Efficient Frontier.
    WHEN TO USE: Standard asset allocation for a balanced portfolio.
    MARKET CONDITION: Bull markets (Max Sharpe) or Bear markets (Min Volatility).
    VERDICT: Tells the Agent the 'ideal' percentage of each stock.
    """
    S = risk_models.fix_nonpositive_semidefinite(S)
    note = None
    if target == "max_sharpe":
        ef, target, note = max_sharpe_or_min_volatility(lambda: EfficientFrontier(mu, S))
    else:
        ef = EfficientFrontier(mu, S)
        ef.min_volatility()

    perf = ef.portfolio_performance()
    return {
        "weights": ef.clean_weights(),
        "expected_return": f"{perf[0]:.2%}",
        "volatility": f"{perf[1]:.2%}",
        "sharpe_ratio": round(perf[2], 2),
        "target_used": target,
        "fallback_note": note,
    }
