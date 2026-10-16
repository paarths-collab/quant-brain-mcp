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
    Describes historical performance; cannot establish safety or future returns.
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


def split_validation_history(price_df, train_fraction=0.7, min_train=126, min_holdout=63):
    """Reserve a later, disjoint period before fitting any portfolio parameters.

    Buy at the first holdout close (after training ends), then hold. No return
    across the training/holdout boundary is claimed or executed retroactively.
    """
    if not 0 < train_fraction < 1:
        raise ValueError("Training fraction must be between zero and one.")
    if not price_df.index.is_monotonic_increasing or not price_df.index.is_unique:
        raise ValueError("Portfolio history must have unique chronological dates.")
    if not np.isfinite(price_df.to_numpy(dtype=float)).all() or (price_df <= 0).any().any():
        raise ValueError("Portfolio history must contain finite, positive prices.")
    split = int(len(price_df) * train_fraction)
    if split < min_train or len(price_df) - split < min_holdout:
        raise ValueError(
            f"Insufficient history for chronological holdout: need at least {min_train} "
            f"training and {min_holdout} holdout observations at a 70/30 split; "
            f"received {len(price_df)}. Request a longer period."
        )
    train = price_df.iloc[:split].copy()
    holdout = price_df.iloc[split:].copy()
    metadata = {
        "method": "chronological_holdout",
        "training_observations": len(train),
        "holdout_observations": len(holdout),
        "training_start": str(train.index[0].date()),
        "training_end": str(train.index[-1].date()),
        "holdout_start": str(holdout.index[0].date()),
        "holdout_end": str(holdout.index[-1].date()),
        "execution": "Buy at first holdout close and hold fixed shares; no rebalancing.",
        "costs_modeled": False,
        "annualization_days": 252,
    }
    return train, holdout, metadata
