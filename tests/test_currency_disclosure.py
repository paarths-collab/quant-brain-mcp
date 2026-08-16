"""Tests for removal of the fake USD normalization (bug C3).

core.forex.normalize_prices divided every Indian price by ONE spot FX rate.
That cancels out exactly in pct_change() (mean/cov/returns), so it never
affected any actual number -- it just gave a false impression that FX risk
was modeled. It is now removed from the optimization path entirely, and the
result carries an explicit fx_note instead of a silent no-op.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd

from main import run_generate_optimized_verdict


def _ohlc(seed, periods=300, start=100.0):
    idx = pd.date_range("2023-01-02", periods=periods, freq="B")
    rng = np.random.default_rng(seed)
    close = pd.Series(start * np.exp(np.cumsum(rng.normal(0.0012, 0.010, periods))), index=idx)
    return pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1_000_000}
    )


def _stub(seed_by_ticker):
    def _fn(ticker, period="2y", interval="1d"):
        if ticker in seed_by_ticker:
            return _ohlc(seed_by_ticker[ticker])
        return {"error": f"No data found for ticker '{ticker}'."}

    return _fn


def test_result_discloses_fx_not_modeled():
    stub = _stub({"AAPL": 1, "RELIANCE.NS": 2, "^GSPC": 3})
    with patch("core.data_loader.fetch_stock_data", side_effect=stub):
        result = run_generate_optimized_verdict(["AAPL", "RELIANCE.NS"], 10000, "mvo")

    assert "error" not in result
    assert "fx_note" in result
    assert "not modeled" in result["fx_note"].lower() or "local" in result["fx_note"].lower()


def test_forex_module_is_no_longer_imported_by_main():
    """main.py must not import the fake conversion at all anymore."""
    import inspect

    import main

    source = inspect.getsource(main.run_generate_optimized_verdict)
    assert "normalize_prices" not in source
    assert "core.forex" not in source


def test_optimization_runs_on_local_currency_prices_directly():
    """Weights must come from unconverted price_df (no normalize_prices call)."""
    stub = _stub({"AAPL": 1, "MSFT": 2, "^GSPC": 3})
    with patch("core.data_loader.fetch_stock_data", side_effect=stub):
        result = run_generate_optimized_verdict(["AAPL", "MSFT"], 10000, "mvo")

    assert "error" not in result
    weights = result["recommended_weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-6
