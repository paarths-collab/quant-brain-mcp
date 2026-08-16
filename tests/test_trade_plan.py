"""Tests for build_trade_plan: the atomic unit of trading.

Given OHLC history, equity, and risk tolerance, produce entry, a structural
stop (swing low or ATR-based, whichever is tighter while staying outside
noise), position size in shares AND currency, max loss, R-multiple targets,
a plain-language invalidation line, and a liquidity check.
"""

import numpy as np
import pandas as pd
import pytest

from tools.trading.trade_plan import compute_trade_plan


def _df(n=120, close_start=100.0, drift=0.001, vol=0.012, seed=7, volume=1_000_000):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(end="2026-08-14", periods=n, freq="B")
    close = pd.Series(close_start * np.exp(np.cumsum(rng.normal(drift, vol, n))), index=idx)
    return pd.DataFrame(
        {
            "Open": close * (1 + rng.normal(0, 0.002, n)),
            "High": close * (1 + np.abs(rng.normal(0.004, 0.003, n))),
            "Low": close * (1 - np.abs(rng.normal(0.004, 0.003, n))),
            "Close": close,
            "Volume": volume,
        }
    )


def test_long_plan_has_all_core_fields():
    plan = compute_trade_plan(_df(), ticker="AAPL", equity=100_000, risk_pct=1.0)
    for key in (
        "ticker", "direction", "as_of", "entry", "stop", "stop_distance",
        "stop_distance_atr", "atr_14", "shares", "position_value",
        "max_loss", "targets", "invalidation", "liquidity", "currency",
    ):
        assert key in plan, f"missing {key}"
    assert plan["direction"] == "long"
    assert plan["currency"] == "USD"


def test_long_stop_below_entry_and_short_above():
    df = _df()
    long_plan = compute_trade_plan(df, ticker="AAPL", equity=100_000, risk_pct=1.0)
    short_plan = compute_trade_plan(df, ticker="AAPL", equity=100_000, risk_pct=1.0, direction="short")
    assert long_plan["stop"] < long_plan["entry"]
    assert short_plan["stop"] > short_plan["entry"]


def test_risk_math_is_consistent():
    """shares * stop_distance must be <= the requested risk amount."""
    equity, risk_pct = 100_000, 1.0
    plan = compute_trade_plan(_df(), ticker="AAPL", equity=equity, risk_pct=risk_pct)
    risk_amount = equity * risk_pct / 100
    assert plan["shares"] > 0
    assert plan["shares"] * plan["stop_distance"] <= risk_amount + 1e-6
    assert plan["max_loss"] == pytest.approx(plan["shares"] * plan["stop_distance"], rel=1e-6)


def test_position_cannot_exceed_equity():
    """No leverage: even with a tight stop, position value stays within equity."""
    # Very low vol -> tight stop -> naive sizing would exceed equity
    plan = compute_trade_plan(
        _df(vol=0.001), ticker="AAPL", equity=10_000, risk_pct=2.0
    )
    assert plan["position_value"] <= 10_000 + 1e-6
    if plan.get("size_capped_by_equity"):
        assert plan["shares"] * plan["entry"] <= 10_000 + 1e-6


def test_targets_are_r_multiples():
    plan = compute_trade_plan(_df(), ticker="AAPL", equity=100_000, risk_pct=1.0)
    r = plan["stop_distance"]
    assert plan["targets"]["1R"] == pytest.approx(plan["entry"] + r, rel=1e-9)
    assert plan["targets"]["2R"] == pytest.approx(plan["entry"] + 2 * r, rel=1e-9)
    assert plan["targets"]["3R"] == pytest.approx(plan["entry"] + 3 * r, rel=1e-9)


def test_short_targets_are_below_entry():
    plan = compute_trade_plan(_df(), ticker="AAPL", equity=100_000, risk_pct=1.0, direction="short")
    assert plan["targets"]["1R"] < plan["entry"]
    assert plan["targets"]["3R"] < plan["targets"]["1R"]


def test_indian_ticker_uses_inr():
    plan = compute_trade_plan(_df(), ticker="RELIANCE.NS", equity=500_000, risk_pct=1.0)
    assert plan["currency"] == "INR"
    assert "₹" in plan["invalidation"] or "below" in plan["invalidation"].lower()


def test_invalidation_mentions_the_stop_price():
    plan = compute_trade_plan(_df(), ticker="AAPL", equity=100_000, risk_pct=1.0)
    assert str(round(plan["stop"], 2)) in plan["invalidation"]


def test_liquidity_reports_order_as_pct_of_turnover():
    plan = compute_trade_plan(_df(volume=50_000), ticker="AAPL", equity=1_000_000, risk_pct=2.0)
    liq = plan["liquidity"]
    assert "avg_daily_turnover_20d" in liq
    assert "order_pct_of_daily_turnover" in liq
    assert liq["order_pct_of_daily_turnover"] >= 0


def test_insufficient_history_returns_error():
    plan = compute_trade_plan(_df(n=10), ticker="AAPL", equity=100_000, risk_pct=1.0)
    assert "error" in plan


def test_unsizeable_when_risk_budget_too_small():
    """If even 1 share exceeds the risk budget, say so instead of shares=0 silently."""
    plan = compute_trade_plan(
        _df(close_start=5000.0, vol=0.03), ticker="AAPL", equity=1_000, risk_pct=0.5
    )
    if plan.get("shares", 1) == 0:
        assert "error" in plan or plan.get("note"), "zero shares must be explained"


def test_invalid_direction_rejected():
    plan = compute_trade_plan(_df(), ticker="AAPL", equity=100_000, risk_pct=1.0, direction="sideways")
    assert "error" in plan


def test_invalid_risk_pct_rejected():
    assert "error" in compute_trade_plan(_df(), ticker="AAPL", equity=100_000, risk_pct=0)
    assert "error" in compute_trade_plan(_df(), ticker="AAPL", equity=100_000, risk_pct=60)
    assert "error" in compute_trade_plan(_df(), ticker="AAPL", equity=-5, risk_pct=1.0)
