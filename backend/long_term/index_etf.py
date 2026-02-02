import pandas as pd
from typing import Dict, List

def analyze_index_etf(
    prices: pd.Series,
    adjusted_prices: pd.Series
) -> Dict:
    if prices.empty or adjusted_prices.empty:
        return {"error": "Insufficient data"}

    horizons = {
        "1Y": 1,
        "3Y": 3,
        "5Y": 5,
        "10Y": 10
    }

    today = adjusted_prices.index[-1]
    results: List[Dict] = []

    daily_returns = adjusted_prices.pct_change().dropna()

    for label, years in horizons.items():
        start_date = today - pd.DateOffset(years=years)
        actual_start = adjusted_prices.index.asof(start_date)

        if pd.isna(actual_start):
            continue

        start_price = adjusted_prices.loc[actual_start]
        end_price = adjusted_prices.loc[today]

        total_return = (end_price / start_price - 1) * 100
        cagr = ((end_price / start_price) ** (1 / years) - 1) * 100

        period_returns = daily_returns.loc[actual_start:today]

        max_dd = ((period_returns + 1).cumprod() /
                  (period_returns + 1).cumprod().cummax() - 1).min() * 100

        volatility = period_returns.std() * (252 ** 0.5) * 100

        results.append({
            "horizon": label,
            "total_return_pct": round(total_return, 2),
            "cagr_pct": round(cagr, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "volatility_pct": round(volatility, 2)
        })

    return {
        "performance": results,
        "metadata": {
            "strategy": "index_etf"
        }
    }
