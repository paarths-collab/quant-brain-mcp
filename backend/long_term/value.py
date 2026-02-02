import pandas as pd
from typing import Dict, Optional

def analyze_value(
    prices: pd.Series,
    quarterly_financials: pd.DataFrame,
    quarterly_balance_sheet: pd.DataFrame,
    shares_outstanding: Optional[int],
    current_metrics: Dict
) -> Dict:
    if prices.empty or quarterly_financials.empty or quarterly_balance_sheet.empty:
        return {"error": "Insufficient data"}

    results = []

    prices = prices.copy()
    prices.index = prices.index.tz_localize(None)

    for col in quarterly_financials.columns[3::4]:  # yearly checkpoints
        try:
            year = col.year
            price = prices.asof(col)

            if price is None or not shares_outstanding:
                continue

            net_income_ttm = quarterly_financials.loc[
                "Net Income",
                col - pd.DateOffset(months=9):col
            ].sum()

            equity = quarterly_balance_sheet.loc[
                "Total Stockholder Equity", col
            ]

            if equity <= 0 or net_income_ttm <= 0:
                continue

            eps = net_income_ttm / shares_outstanding
            pe = price / eps if eps > 0 else None
            pb = price / (equity / shares_outstanding)
            roe = net_income_ttm / equity * 100

            results.append({
                "year": year,
                "pe_ratio": pe,
                "pb_ratio": pb,
                "roe_pct": roe
            })

        except KeyError:
            continue

    results.sort(key=lambda x: x["year"])

    return {
        "current_metrics": {
            "pe": current_metrics.get("trailingPE"),
            "pb": current_metrics.get("priceToBook"),
            "roe": current_metrics.get("returnOnEquity"),
            "debt_to_equity": current_metrics.get("debtToEquity")
        },
        "historical_metrics": results,
        "metadata": {
            "strategy": "value_investing"
        }
    }
