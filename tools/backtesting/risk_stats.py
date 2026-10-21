import vectorbt as vbt

from core.risk_state import unavailable


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
        "alpha": stats["Alpha"] if "Alpha" in stats else unavailable("Backtest engine did not report alpha"),
        "beta": stats["Beta"] if "Beta" in stats else unavailable("Backtest engine did not report beta"),
    }
