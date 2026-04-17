from pypfopt import EfficientFrontier, objective_functions


def run_constrained_mvo(mu, S, weight_bounds=(0, 0.2), l2_reg=0.1):
    """
    STRATEGY: Adding guardrails to the optimization.
    WHEN TO USE: When the Agent wants to prevent 'Concentration Risk'.
    L2 REGULARIZATION: Forces weights to be more spread out (no 100% in one stock).
    BOUNDS: e.g., (0, 0.2) means no stock can be more than 20% of the portfolio.
    """
    ef = EfficientFrontier(mu, S, weight_bounds=weight_bounds)
    ef.add_objective(objective_functions.L2_reg, gamma=l2_reg)

    ef.max_sharpe()
    return {"weights": ef.clean_weights(), "weight_bounds": weight_bounds, "l2_reg": l2_reg}
