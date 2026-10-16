"""Independent arithmetic benchmarks and invalid-provider boundary checks.

These use fixed, hand-checkable data rather than a model's agreement with itself.
"""
import json
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from tools.backtesting.portfolio_bt import backtest_optimized_portfolio, split_validation_history
from tools.trading.quotes import get_quotes
from tools.trading.trade_plan import compute_trade_plan


def bars():
    return pd.DataFrame(
        {"Open": 100., "High": 100.67, "Low": 99.33, "Close": 100., "Volume": 1000000},
        index=pd.bdate_range("2025-01-01", periods=60),
    )


def test_buy_and_hold_matches_independent_share_ledger():
    prices = pd.DataFrame({"RELIANCE.NS": [100., 120., 90., 110.], "TCS.NS": [100., 100., 110., 100.]},
                          index=pd.bdate_range("2025-01-01", periods=4))
    # 100 rupees buys .6 and .4 shares. Ledger: 100,112,98,106.
    # Return = 6%; peak-to-trough loss = (112-98)/112 = 12.5%.
    result = backtest_optimized_portfolio(prices, {"TCS.NS": .4, "RELIANCE.NS": .6})
    assert result["portfolio_total_return"] == "6.00%"
    assert result["portfolio_drawdown"] == "12.50%"


@pytest.mark.parametrize("direction", ["long", "short"])
def test_displayed_trade_plan_never_exceeds_risk_budget_after_rounding(direction):
    result = compute_trade_plan(bars(), "RELIANCE.NS", 100000, 1, direction)
    assert "error" not in result
    distance = abs(result["entry"] - result["stop"])
    assert result["max_loss"] == pytest.approx(result["shares"] * distance)
    assert result["max_loss"] <= 1000
    assert result["position_value"] == pytest.approx(result["shares"] * result["entry"])
    assert result["currency"] == "INR"


@pytest.mark.parametrize("equity", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_equity_returns_error_without_sizing(equity):
    assert "error" in compute_trade_plan(bars(), "RELIANCE.NS", equity)


@pytest.mark.parametrize("mutation", ["nan", "negative", "missing", "duplicates", "reversed"])
def test_invalid_history_is_rejected_before_trade_sizing(mutation):
    frame = bars()
    if mutation == "nan":
        frame.iloc[-1, frame.columns.get_loc("Close")] = np.nan
    elif mutation == "negative":
        frame["Close"] = -1
    elif mutation == "missing":
        frame = frame.drop(columns="Volume")
    elif mutation == "duplicates":
        frame.index = [frame.index[0]] * len(frame)
    else:
        frame = frame.iloc[::-1]
    assert "error" in compute_trade_plan(frame, "RELIANCE.NS", 100000)


@pytest.mark.parametrize("last", [float("nan"), float("inf"), -1., 0., "unavailable"])
def test_invalid_quote_price_is_not_a_successful_quote(last):
    ticker = MagicMock()
    ticker.fast_info = {"lastPrice": last}
    with patch("yfinance.Ticker", return_value=ticker):
        result = get_quotes(["RELIANCE.NS"])
    assert "error" in result["quotes"]["RELIANCE.NS"]
    json.dumps(result, allow_nan=False)


def test_missing_observation_time_is_not_claimed_as_live_market_time():
    ticker = MagicMock()
    ticker.fast_info = {"lastPrice": 100., "previousClose": float("nan"), "lastVolume": float("inf")}
    with patch("yfinance.Ticker", return_value=ticker):
        result = get_quotes(["RELIANCE.NS"])
    quote = result["quotes"]["RELIANCE.NS"]
    assert quote["last_price"] == 100
    assert quote["previous_close"] is None
    assert quote["volume"] is None
    assert result["market_timestamp"] is None
    assert result["freshness_status"] == "unknown"
    assert result["as_of"] == result["fetched_at"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("corruption", ["future_first", "duplicate", "missing_price"])
def test_holdout_rejects_histories_that_cannot_support_chronological_validation(corruption):
    frame = pd.DataFrame({"RELIANCE.NS": np.linspace(100, 200, 300)},
                         index=pd.bdate_range("2024-01-01", periods=300))
    if corruption == "future_first":
        frame = frame.iloc[::-1]
    elif corruption == "duplicate":
        frame.index = [frame.index[0]] * len(frame)
    else:
        frame.iloc[230, 0] = np.nan
    with pytest.raises(ValueError):
        split_validation_history(frame)


def test_numeric_strings_are_coerced_before_price_arithmetic():
    result = compute_trade_plan(bars().astype(str), "RELIANCE.NS", 100000)
    assert "error" not in result
    assert result["entry"] == 100


def test_large_finite_equity_does_not_overflow_intermediate_risk_product():
    result = compute_trade_plan(bars(), "RELIANCE.NS", 1e308, risk_pct=2)
    assert "error" not in result
    assert np.isfinite(result["risk_budget"])
    json.dumps(result, allow_nan=False)
