import vectorbt as vbt


def get_risk_analysis(pf):
    """
    STRATEGY: Detailed Risk decomposition.
    METRICS: Expectancy, Profit Factor, Max Drawdown Duration.
    WHEN TO USE: When the user asks 'What is the worst that can happen?'
    """
    stats = pf.stats()
    return {
        "expectancy": stats["Expectancy"],
        "profit_factor": stats["Profit Factor"],
        "max_drawdown_duration": stats["Max Drawdown Duration"],
        "alpha": stats.get("Alpha", "N/A"),
        "beta": stats.get("Beta", "N/A"),
    }
