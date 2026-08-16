"""Regression tests for two verified correctness bugs:

1. Portfolio weights were assigned positionally, scrambling them onto the
   wrong tickers whenever the optimizer returned a non-column order.
2. vectorbt annualized Sharpe with 365 days instead of 252 trading days,
   inflating every Sharpe ratio by sqrt(365/252) = 1.2035x.
"""

import math

import numpy as np
import pandas as pd
import pytest
import vectorbt as vbt

import core.quant_settings  # noqa: F401  (applies settings on import)


# --------------------- annualization convention ---------------------


def test_year_freq_is_252_trading_days():
    assert pd.Timedelta(vbt.settings["returns"]["year_freq"]) == pd.Timedelta(days=252)


def test_sharpe_uses_trading_day_annualization():
    """A known return series must annualize with sqrt(252), not sqrt(365)."""
    rng = np.random.default_rng(0)
    idx = pd.date_range("2023-01-02", periods=300, freq="B")
    rets = pd.Series(rng.normal(0.0005, 0.01, len(idx)), index=idx)

    expected = (rets.mean() / rets.std()) * math.sqrt(252)
    actual = rets.vbt.returns(freq="1D").sharpe_ratio()
    assert actual == pytest.approx(expected, rel=1e-6)


# --------------------- portfolio weight alignment ---------------------


def _price_frame(columns, periods=30):
    idx = pd.date_range("2024-01-01", periods=periods, freq="B")
    data = {c: np.linspace(100, 120, periods) for c in columns}
    return pd.DataFrame(data, index=idx)


def test_weights_align_by_ticker_not_position():
    """Optimizer weight dicts often arrive in a different order than columns."""
    from tools.backtesting.portfolio_bt import _weights_row

    columns = pd.Index(["AAPL", "MSFT", "NVDA"])
    weights = {"NVDA": 0.6, "AAPL": 0.3, "MSFT": 0.1}

    row = _weights_row(weights, columns)
    assert list(row) == [0.3, 0.1, 0.6], "weights must map to their own tickers"


def test_weights_row_handles_missing_ticker():
    from tools.backtesting.portfolio_bt import _weights_row

    columns = pd.Index(["AAPL", "MSFT", "NVDA"])
    row = _weights_row({"AAPL": 0.5, "NVDA": 0.5}, columns)
    assert list(row) == [0.5, 0.0, 0.5]


def test_weights_row_accepts_series():
    from tools.backtesting.portfolio_bt import _weights_row

    columns = pd.Index(["AAPL", "MSFT"])
    row = _weights_row(pd.Series({"MSFT": 0.7, "AAPL": 0.3}), columns)
    assert list(row) == [0.3, 0.7]


def test_backtest_is_order_invariant():
    """Same economic portfolio, different dict order -> identical results."""
    from tools.backtesting.portfolio_bt import backtest_optimized_portfolio

    columns = ["AAPL", "MSFT", "NVDA"]
    price_df = _price_frame(columns)

    ordered = {"AAPL": 0.2, "MSFT": 0.3, "NVDA": 0.5}
    shuffled = {"NVDA": 0.5, "AAPL": 0.2, "MSFT": 0.3}

    a = backtest_optimized_portfolio(price_df, ordered)
    b = backtest_optimized_portfolio(price_df, shuffled)
    assert a["portfolio_total_return"] == b["portfolio_total_return"]
    assert a["portfolio_sharpe"] == b["portfolio_sharpe"]
