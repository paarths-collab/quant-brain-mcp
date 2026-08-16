import numpy as np
import pandas as pd
import vectorbt as vbt


def _wilder_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """Compute RSI using Wilder smoothing for broad compatibility.

    Warmup bars (before `length` observations exist) are left as NaN. They must
    not be backfilled: doing so copies a future value backwards and lets signals
    fire on information that did not exist at that bar (lookahead bias).
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()

    rsi = pd.Series(np.nan, index=close.index, dtype=float)
    defined = avg_gain.notna() & avg_loss.notna()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi[defined] = (100 - (100 / (1 + rs)))[defined]

    # No downward movement in the window: RSI is 100 by definition (not NaN).
    rsi[defined & (avg_loss == 0) & (avg_gain > 0)] = 100.0
    # Perfectly flat window: neither gains nor losses, treat as neutral.
    rsi[defined & (avg_loss == 0) & (avg_gain == 0)] = 50.0

    return rsi


def run_backtest(df, length=14, lower=30, upper=70):
    """Vectorized backtest for RSI mean reversion."""
    close = df["Close"].astype(float)
    rsi = _wilder_rsi(close, length=length)
    entries = rsi < lower
    exits = rsi > upper

    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=0.001, freq="1D")
    stats = pf.stats()

    returns = pf.returns().dropna()
    sharpe_ratio = np.nan
    if len(returns) > 2 and returns.std() > 1e-12:
        sharpe_ratio = float((returns.mean() / returns.std()) * np.sqrt(252))

    return {
        "strategy_name": "RSI Mean Reversion",
        "total_return": f"{stats['Total Return [%]']:.2f}%",
        "sharpe_ratio": None if np.isnan(sharpe_ratio) else round(sharpe_ratio, 2),
        "win_rate": f"{stats['Win Rate [%]']:.2f}%",
        "max_drawdown": f"{stats['Max Drawdown [%]']:.2f}%",
        "expectancy": stats.get('Expectancy', None),
    }
