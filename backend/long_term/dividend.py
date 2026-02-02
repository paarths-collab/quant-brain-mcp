import pandas as pd
from typing import Dict, List

def analyze_dividends(
    dividends: pd.Series,
    prices: pd.Series,
    payout_ratio: float | None = None
) -> Dict:
    """
    dividends: Series indexed by date (cash dividends)
    prices: Series indexed by date (close prices)
    """

    if dividends.empty or prices.empty:
        return {"error": "The Company has not paid any dividends in the last 10 years"}

    # Normalize indices
    dividends = dividends.copy()
    prices = prices.copy()

    dividends.index = dividends.index.tz_localize(None)
    prices.index = prices.index.tz_localize(None)

    # Current yield
    latest_price = prices.iloc[-1]
    trailing_12m_div = dividends[dividends.index >= prices.index[-1] - pd.DateOffset(months=12)].sum()

    current_yield = (trailing_12m_div / latest_price) * 100 if latest_price > 0 else None

    # Yearly dividends
    yearly_divs = dividends.resample("YE").sum()

    historical = []
    periods = [1, 3, 5, 10]
    today = yearly_divs.index.max()

    for years in periods:
        start = today - pd.DateOffset(years=years)
        period = yearly_divs[yearly_divs.index >= start]

        if len(period) < 2:
            continue

        start_div, end_div = period.iloc[0], period.iloc[-1]
        actual_years = (period.index[-1] - period.index[0]).days / 365.25

        cagr = (
            ((end_div / start_div) ** (1 / actual_years) - 1) * 100
            if start_div > 0 and actual_years > 0
            else None
        )

        price_at_start = prices.asof(period.index[0])
        avg_yoc = (period.mean() / price_at_start) * 100 if price_at_start else None

        historical.append({
            "period_years": years,
            "dividend_cagr_pct": cagr,
            "avg_yield_on_cost_pct": avg_yoc
        })

    return {
        "current_metrics": {
            "current_yield_pct": current_yield,
            "payout_ratio_pct": payout_ratio * 100 if payout_ratio else None
        },
        "historical_metrics": historical
    }
