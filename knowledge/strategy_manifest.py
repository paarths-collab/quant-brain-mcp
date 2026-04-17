VERDICT_LOGIC = {
    "backtest_metrics": {
        "sharpe_ratio": {
            "good": "> 1.0",
            "excellent": "> 2.0",
            "poor": "< 0.5 (Do not recommend)",
        },
        "win_rate": {
            "stable": "> 55%",
            "high_conviction": "> 65%",
        },
        "max_drawdown": {
            "conservative": "< 10%",
            "aggressive": "< 25%",
            "dangerous": "> 30%",
        },
    },
    "verdict_types": {
        "STRONG_BUY": "High Sharpe (>1.5) + High Win Rate (>60%) + Low Drawdown (<15%)",
        "RISKY_MOMENTUM": "High Return (>30%) but High Drawdown (>25%). Advise small position size.",
        "STAY_AWAY": "Negative returns in backtest or Sharpe < 0.3.",
        "HEDGE_REQUIRED": "Positive returns but high correlation between assets. Suggest HRP Optimization.",
    },
}
