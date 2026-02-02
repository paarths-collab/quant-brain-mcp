import pandas as pd
import numpy as np

def run_dca(
    price_series: pd.Series,
    monthly_investment: float
) -> dict:
    """
    price_series: Monthly close prices (indexed by datetime)
    """

    if price_series.empty:
        return {"error": "Empty price series"}

    units_bought = monthly_investment / price_series
    total_units = units_bought.cumsum()
    
    n_months = len(price_series)
    cumulative_investment = monthly_investment * np.arange(1, n_months + 1)

    df = pd.DataFrame({
        "Monthly Price": price_series,
        "Invested This Month": monthly_investment,
        "Units Bought": units_bought,
        "Total Units": total_units,
        "Total Capital Invested": cumulative_investment,
        "Portfolio Value": total_units * price_series,
    })

    final_value = df["Portfolio Value"].iloc[-1]
    total_invested = df["Total Capital Invested"].iloc[-1]

    return {
        "equity_curve": df["Portfolio Value"],
        "invested_curve": df["Total Capital Invested"],
        "metrics": {
            "total_invested": float(total_invested),
            "final_value": float(final_value),
            "total_return_pct": (final_value / total_invested - 1) * 100,
            "months": len(df),
        }
    }
