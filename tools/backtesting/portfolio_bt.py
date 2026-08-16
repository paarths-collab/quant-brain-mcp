import vectorbt as vbt
import numpy as np
import pandas as pd

from core import quant_settings  # noqa: F401  (252-day annualization)


def _weights_row(weights, columns):
    """Map a weight mapping onto `columns` BY TICKER, returning a positional array.

    `df.iloc[0] = pd.Series(weights)` assigns positionally and ignores the
    Series index, so any optimizer returning weights in a different order than
    price_df.columns (hrp, cvar, semivariance, black_litterman) had its weights
    silently transposed onto the wrong tickers. Reindexing by name first makes
    the assignment order-independent.
    """
    return pd.Series(dict(weights)).reindex(columns).fillna(0.0).to_numpy(dtype=float)


def backtest_optimized_portfolio(price_df, weights):
    """
    STRATEGY: Multi-asset allocation backtest.
    INPUT: price_df (Close prices of all stocks), weights (from PyPortfolioOpt).
    WHEN TO USE: To verify if the AI's suggested portfolio is actually safe.
    """
    # Create an order dataframe that only buys at the first timestep
    weights_df = pd.DataFrame(index=price_df.index, columns=price_df.columns, data=np.nan)
    weights_df.iloc[0] = _weights_row(weights, price_df.columns)

    pf = vbt.Portfolio.from_orders(
        price_df,
        size=weights_df,
        size_type="target_percent",
        group_by=True,
        cash_sharing=True,
        freq="1D", # Add daily frequency to fix Sharpe/Calmar warnings
    )

    stats = pf.stats()
    return {
        "portfolio_total_return": f"{stats['Total Return [%]']:.2f}%",
        "portfolio_sharpe": round(stats['Sharpe Ratio'], 2),
        "portfolio_drawdown": f"{stats['Max Drawdown [%]']:.2f}%",
        "portfolio_total_trades": stats["Total Trades"],
    }
