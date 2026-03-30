"""
Isolated long_term_strategy for portfolio/core.
Self-contained buy-and-hold / asset allocation strategy runner.
Modifying this does NOT affect any other module.
"""
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Any, List, Optional


def run_long_term_strategy(
    tickers: List[str],
    allocation: Optional[Dict[str, float]] = None,
    start_date: str = "2020-01-01",
    initial_capital: float = 100000,
) -> Dict[str, Any]:
    """
    Run a long-term portfolio strategy with equal or custom allocation.

    Args:
        tickers: List of ticker symbols
        allocation: Dict of {ticker: weight} (must sum to ~1.0). Equal if None.
        start_date: Strategy start date in YYYY-MM-DD format
        initial_capital: Starting portfolio value

    Returns:
        Portfolio performance metrics and equity curve.
    """
    if not tickers:
        return {"error": "No tickers provided"}

    try:
        import pandas as pd
        # Set equal allocation if not provided
        if not allocation:
            weight = 1.0 / len(tickers)
            allocation = {t.upper(): weight for t in tickers}
        else:
            allocation = {k.upper(): v for k, v in allocation.items()}

        # Normalize weights to sum to 1
        total = sum(allocation.values())
        if total > 0:
            allocation = {k: v / total for k, v in allocation.items()}

        # Fetch close prices
        data = {}
        for ticker in tickers:
            try:
                hist = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
                if not hist.empty:
                    data[ticker.upper()] = hist["Close"]
            except Exception as e:
                print(f"[long_term_strategy] Failed to fetch {ticker}: {e}")

        if not data:
            return {"error": "Could not fetch data for any ticker"}

        prices = pd.DataFrame(data).dropna()
        if prices.empty:
            return {"error": "No overlapping price data"}

        # Compute portfolio returns
        returns = prices.pct_change().dropna()
        weighted_returns = sum(
            returns[t] * allocation.get(t, 0)
            for t in returns.columns
            if t in allocation
        )

        equity = initial_capital * (1 + weighted_returns).cumprod()
        total_return = (equity.iloc[-1] / initial_capital - 1) * 100
        max_drawdown = ((equity / equity.cummax()) - 1).min() * 100
        annualized_return = ((equity.iloc[-1] / initial_capital) ** (252 / len(equity)) - 1) * 100
        sharpe = (weighted_returns.mean() / weighted_returns.std()) * np.sqrt(252) if weighted_returns.std() != 0 else 0

        # Equity curve for charting
        curve = [
            {"date": str(idx.date()), "value": round(float(val), 2)}
            for idx, val in equity.items()
        ]

        return {
            "tickers": tickers,
            "allocation": allocation,
            "initial_capital": initial_capital,
            "final_value": round(float(equity.iloc[-1]), 2),
            "total_return": round(float(total_return), 2),
            "annualized_return": round(float(annualized_return), 2),
            "max_drawdown": round(float(max_drawdown), 2),
            "sharpe_ratio": round(float(sharpe), 2),
            "equity_curve": curve,
            "status": "success",
        }

    except Exception as e:
        print(f"[long_term_strategy] Error: {e}")
        return {"error": str(e), "status": "error"}
