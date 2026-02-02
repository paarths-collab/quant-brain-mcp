import pandas as pd
from backend.services.risk_metrics import evaluate_risk
from backend.services.risk_profiles import RISK_PROFILES

dates = pd.date_range("2024-01-01", periods=10)

equity = pd.Series(
    [100000, 101000, 102000, 98000, 96000, 95000, 94000, 94500, 96000, 97000],
    index=dates
)

returns = equity.pct_change().fillna(0)

benchmark = returns * 0.8  # synthetic benchmark

profile = RISK_PROFILES["capital_preservation"]

risk_report = evaluate_risk(
    equity=equity,
    returns=returns,
    benchmark_returns=benchmark,
    profile=profile
)

print("\n✅ Risk Profile:", "capital_preservation")
print("Drawdown:", risk_report["drawdown"])
print("Volatility:", risk_report["volatility"])
print("Violations:", risk_report["violations"])
print("Action:", risk_report["drawdown_action"])
