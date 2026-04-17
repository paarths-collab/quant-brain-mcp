OPTIMIZATION_KNOWLEDGE = {
    "mean_variance": {
        "file": "mean_variance.py",
        "goal": "Max Sharpe Ratio.",
        "use_case": "Standard growth investors. Finds the 'Efficient Frontier'.",
        "risk_level": "Medium - dependent on historical accuracy.",
    },
    "hrp": {
        "file": "hrp_cla_optimizers.py",
        "goal": "Hierarchical Risk Parity (Diversity).",
        "use_case": "Crisis management. Clusters stocks to ensure no one sector crashes the portfolio.",
        "risk_level": "Lowest - best for uncertain markets (India/US volatility).",
    },
    "black_litterman": {
        "file": "black_litterman.py",
        "goal": "AI Insights + Market Equilibrium.",
        "use_case": "When the Agent has a 'Strong Verdict' on a specific stock (e.g., 'NVDA will outperform').",
        "risk_level": "Variable - based on the accuracy of the 'Views'.",
    },
    "cvar_tail_risk": {
        "file": "efficient_frontier.py",
        "goal": "Conditional Value at Risk (Minimize worst-case).",
        "use_case": "Conservative investors who fear a 'Market Crash'.",
        "risk_level": "Defensive - protects the downside.",
    },
}
