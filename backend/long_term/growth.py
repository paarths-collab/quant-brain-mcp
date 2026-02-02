import pandas as pd
from typing import Dict, List, Optional

def analyze_growth(
    financials: pd.DataFrame,
    prices: pd.Series,
    revenue_growth_q: Optional[float],
    earnings_growth_q: Optional[float],
) -> Dict:
    """
    financials: Annual income statement (columns = fiscal dates)
    prices: Daily close prices
    """

    if financials.empty or prices.empty:
        return {"error": "Insufficient data"}

    prices = prices.copy()
    prices.index = prices.index.tz_localize(None)

    results = []

    for i in range(len(financials.columns) - 1):
        try:
            curr_date = financials.columns[i]
            prev_date = financials.columns[i + 1]
            year = curr_date.year

            curr_rev = financials.loc["Total Revenue", curr_date]
            prev_rev = financials.loc["Total Revenue", prev_date]

            if prev_rev <= 0:
                continue

            revenue_growth_yoy = ((curr_rev - prev_rev) / prev_rev) * 100

            price_curr = prices.asof(curr_date)
            price_prev = prices.asof(prev_date)

            if price_prev and price_prev > 0:
                price_growth_yoy = ((price_curr - price_prev) / price_prev) * 100
            else:
                price_growth_yoy = None

            results.append({
                "year": year,
                "revenue_growth_yoy_pct": revenue_growth_yoy,
                "price_growth_yoy_pct": price_growth_yoy,
            })

        except KeyError:
            continue

    results.reverse()

    return {
        "current_metrics": {
            "revenue_growth_q_yoy_pct": revenue_growth_q * 100 if revenue_growth_q else None,
            "earnings_growth_q_yoy_pct": earnings_growth_q * 100 if earnings_growth_q else None,
        },
        "historical_metrics": results,
        "metadata": {
            "strategy": "growth_investing"
        }
    }
