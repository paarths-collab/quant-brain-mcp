# services/metrics.py

import numpy as np

def calculate_metrics(equity_df, trades, initial_capital):
    final_equity = equity_df["Equity_Curve"].iloc[-1]
    returns = equity_df["Equity_Curve"].pct_change().dropna()

    sharpe = (
        np.sqrt(252) * returns.mean() / returns.std()
        if returns.std() != 0 else 0
    )

    peak = equity_df["Equity_Curve"].cummax()
    drawdown = (equity_df["Equity_Curve"] - peak) / peak

    return {
        "Total Return %": round((final_equity / initial_capital - 1) * 100, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Max Drawdown %": round(drawdown.min() * 100, 2),
        "Number of Trades": len(trades),
    }
