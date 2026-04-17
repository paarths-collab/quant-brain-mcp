import vectorbt as vbt
import numpy as np
import pandas as pd


def backtest_optimized_portfolio(price_df, weights):
    """
    STRATEGY: Multi-asset allocation backtest.
    INPUT: price_df (Close prices of all stocks), weights (from PyPortfolioOpt).
    WHEN TO USE: To verify if the AI's suggested portfolio is actually safe.
    """
    # Create an order dataframe that only buys at the first timestep
    weights_df = pd.DataFrame(index=price_df.index, columns=price_df.columns, data=np.nan)
    weights_df.iloc[0] = pd.Series(weights)

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
