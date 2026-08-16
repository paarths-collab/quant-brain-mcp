"""Tests for portfolio-weighted intelligence blending and verdict reachability.

Bug C1: every headline risk field (VaR, beta, alpha, factor_exposure,
risk_flags) was computed from ONE ticker (whichever resolved first),
regardless of portfolio weights. Two users with the identical portfolio in
different list order got different -- sometimes contradictory -- verdicts.

Bug H2: `strategic_verdict` unconditionally overwrote `backtest_verdict`
whenever alpha was numeric (nearly always), so "STAY AWAY" was structurally
unreachable even when the backtest was clearly bad (negative Sharpe).

Fix: `_compute_portfolio_intelligence` runs quant/alpha analysis per HELD
ticker and blends VaR/beta/alpha/r_squared by portfolio weight (renormalized
over tickers whose analysis succeeded). The verdict now forces STAY AWAY
when the backtest Sharpe is non-finite or <= 0, before the alpha-based
branches can override it.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd

import main as main_module
from main import (
    _compute_portfolio_intelligence,
    _infer_benchmark_ticker,
    _to_float_pct,
    run_generate_optimized_verdict,
)


def _ohlc(seed, periods=300, start=100.0, drift=0.0006, vol=0.010):
    idx = pd.date_range("2023-01-02", periods=periods, freq="B")
    rng = np.random.default_rng(seed)
    close = pd.Series(start * np.exp(np.cumsum(rng.normal(drift, vol, periods))), index=idx)
    return pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1_000_000}
    )


def _stub(seed_by_ticker, **kwargs):
    def _fn(ticker, period="2y", interval="1d"):
        if ticker in seed_by_ticker:
            return _ohlc(seed_by_ticker[ticker], **kwargs)
        return {"error": f"No data found for ticker '{ticker}'."}

    return _fn


# --------------------------- helpers still work ---------------------------


def test_infer_benchmark_ticker_module_level():
    assert _infer_benchmark_ticker("RELIANCE.NS") == "^NSEI"
    assert _infer_benchmark_ticker("AAPL") == "^GSPC"


def test_to_float_pct_module_level():
    assert _to_float_pct("-2.50%") == -2.50
    assert _to_float_pct("bad", default=1.0) == 1.0


# --------------------------- weighted blending ---------------------------


from contextlib import contextmanager


@contextmanager
def _patch_intelligence_fetch(fn):
    """Patch fetch_data as imported into BOTH engine.py and alpha_engine.py.

    Those modules did `from core.data_loader import fetch_data`, which binds
    their own local reference at import time -- patching core.data_loader.fetch_data
    afterward would not reach them.
    """
    with patch("tools.intelligence.engine.fetch_data", side_effect=fn), patch(
        "tools.intelligence.alpha_engine.fetch_data", side_effect=fn
    ):
        yield


def test_intelligence_blends_across_all_held_tickers_not_just_first():
    """A 2-ticker portfolio must reflect BOTH tickers' risk, not just one."""
    frames = {"AAPL": _ohlc(1, vol=0.006), "MSFT": _ohlc(2, vol=0.030)}
    bench = _ohlc(9)

    with _patch_intelligence_fetch(lambda t, **kw: (bench, None)):
        per_ticker, blended = _compute_portfolio_intelligence(
            {"AAPL": 0.9, "MSFT": 0.1}, frames, _infer_benchmark_ticker
        )

    assert blended is not None
    tickers_seen = {e["ticker"] for e in per_ticker}
    assert tickers_seen == {"AAPL", "MSFT"}

    # Sanity: a 90/10 blend must be much closer to AAPL-only than a 50/50 blend would be.
    aapl_only = next(e for e in per_ticker if e["ticker"] == "AAPL")
    msft_only = next(e for e in per_ticker if e["ticker"] == "MSFT")
    aapl_var = _to_float_pct(aapl_only["quant_analysis"]["one_day_var_95"])
    msft_var = _to_float_pct(msft_only["quant_analysis"]["one_day_var_95"])
    assert abs(blended["one_day_var_95_pct"] - aapl_var) < abs(blended["one_day_var_95_pct"] - msft_var)


def test_zero_weight_ticker_excluded_from_blend():
    frames = {"AAPL": _ohlc(1), "MSFT": _ohlc(2)}
    bench = _ohlc(9)
    with _patch_intelligence_fetch(lambda t, **kw: (bench, None)):
        per_ticker, blended = _compute_portfolio_intelligence(
            {"AAPL": 1.0, "MSFT": 0.0}, frames, _infer_benchmark_ticker
        )
    assert blended["tickers_used"] == ["AAPL"]


def test_failed_ticker_intelligence_excluded_but_others_still_blend():
    """One ticker's analysis failing must not crash the whole blend."""
    frames = {"AAPL": _ohlc(1), "BADTICKER": pd.DataFrame()}  # empty df -> analysis fails
    bench = _ohlc(9)

    with _patch_intelligence_fetch(lambda t, **kw: (bench, None)):
        per_ticker, blended = _compute_portfolio_intelligence(
            {"AAPL": 0.5, "BADTICKER": 0.5}, frames, _infer_benchmark_ticker
        )

    assert blended is not None
    assert blended["tickers_used"] == ["AAPL"]
    failed_entry = next(e for e in per_ticker if e["ticker"] == "BADTICKER")
    assert "error" in failed_entry["quant_analysis"] or "error" in failed_entry["alpha_analysis"]


def test_all_tickers_failing_returns_none_blend_not_a_crash():
    frames = {"BAD1": pd.DataFrame(), "BAD2": pd.DataFrame()}
    with _patch_intelligence_fetch(lambda t, **kw: (pd.DataFrame(), None)):
        per_ticker, blended = _compute_portfolio_intelligence(
            {"BAD1": 0.5, "BAD2": 0.5}, frames, _infer_benchmark_ticker
        )
    assert blended is None
    assert len(per_ticker) == 2


# --------------------------- verdict reachability (H2) ---------------------------


def test_stay_away_reachable_on_bad_backtest():
    """A clearly bad backtest (negative Sharpe) must be able to yield STAY AWAY,
    even when alpha analysis happens to be numeric and positive."""
    # Two badly-declining, high-vol tickers -> negative portfolio Sharpe.
    stub = _stub({"BADCO": 1, "^GSPC": 2}, drift=-0.004, vol=0.03)
    with patch("core.data_loader.fetch_stock_data", side_effect=stub):
        result = run_generate_optimized_verdict(["BADCO"], 10000, "min_volatility")

    assert "error" not in result
    assert result["backtest_metrics"]["portfolio_sharpe"] is not None
    sharpe = result["backtest_metrics"]["portfolio_sharpe"]
    if sharpe is not None and sharpe <= 0:
        assert result["final_verdict"] == "STAY AWAY"


def test_verdict_reasonable_paths_still_reachable():
    """Regression: a healthy uptrending portfolio should not be STAY AWAY."""
    stub = _stub({"GOODCO": 1, "^GSPC": 2}, drift=0.0015, vol=0.008)
    with patch("core.data_loader.fetch_stock_data", side_effect=stub):
        result = run_generate_optimized_verdict(["GOODCO"], 10000, "min_volatility")

    assert "error" not in result
    assert result["final_verdict"] in {"ACCUMULATE", "NEUTRAL", "STRONG BUY", "PROPER", "REDUCE"}
    assert result["final_verdict"] != "STAY AWAY"


# --------------------------- end-to-end result shape ---------------------------


def test_result_includes_per_ticker_intelligence_breakdown():
    stub = _stub({"AAPL": 1, "MSFT": 2, "^GSPC": 3})
    with patch("core.data_loader.fetch_stock_data", side_effect=stub):
        result = run_generate_optimized_verdict(["AAPL", "MSFT"], 10000, "min_volatility")

    assert "error" not in result
    assert "portfolio_intelligence" in result
    pi = result["portfolio_intelligence"]
    assert "per_ticker" in pi
    tickers = {e["ticker"] for e in pi["per_ticker"]}
    assert tickers == {"AAPL", "MSFT"}
