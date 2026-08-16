"""Tests for scan_watchlist: the weekly-habit tool.

One call over a list of tickers -> per name: last close, distance from key
moving averages, ATR%, 52-week-high distance, volume spike, and which alert
rules fired -- sorted so the most actionable names come first.
"""

import numpy as np
import pandas as pd

from tools.trading.watchlist import scan_frames


def _frame(n=300, start=100.0, drift=0.0005, vol=0.012, seed=1, last_volume_mult=1.0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(end="2026-08-14", periods=n, freq="B")
    close = pd.Series(start * np.exp(np.cumsum(rng.normal(drift, vol, n))), index=idx)
    volume = pd.Series(1_000_000.0, index=idx)
    volume.iloc[-1] *= last_volume_mult
    return pd.DataFrame(
        {
            "Open": close.shift(1).fillna(close.iloc[0]),
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": volume,
        }
    )


def test_scan_reports_every_ticker():
    frames = {"AAA": _frame(seed=1), "BBB": _frame(seed=2)}
    result = scan_frames(frames)
    assert {r["ticker"] for r in result["results"]} == {"AAA", "BBB"}


def test_core_fields_present():
    result = scan_frames({"AAA": _frame()})
    row = result["results"][0]
    for key in (
        "ticker", "last_close", "as_of", "day_change_pct",
        "pct_from_20dma", "pct_from_50dma", "pct_from_200dma",
        "atr_pct", "pct_from_52w_high", "volume_vs_20d_avg",
        "rules_fired",
    ):
        assert key in row, f"missing {key}"


def test_volume_spike_rule_fires():
    frames = {"SPIKE": _frame(last_volume_mult=4.0), "QUIET": _frame(seed=5)}
    result = scan_frames(frames)
    by = {r["ticker"]: r for r in result["results"]}
    assert "volume_spike" in by["SPIKE"]["rules_fired"]
    assert "volume_spike" not in by["QUIET"]["rules_fired"]


def test_near_52w_high_rule():
    # Steady strong uptrend ends at/near its high
    frames = {"HIGH": _frame(drift=0.003, vol=0.004, seed=3)}
    result = scan_frames(frames)
    row = result["results"][0]
    assert row["pct_from_52w_high"] > -3.0
    assert "near_52w_high" in row["rules_fired"]


def test_sorted_by_rule_hits_descending():
    frames = {
        "BUSY": _frame(drift=0.003, vol=0.004, seed=3, last_volume_mult=4.0),
        "DEAD": _frame(drift=0.0, vol=0.01, seed=9),
    }
    result = scan_frames(frames)
    hits = [len(r["rules_fired"]) for r in result["results"]]
    assert hits == sorted(hits, reverse=True)


def test_failed_ticker_reported_not_dropped():
    frames = {"GOOD": _frame(), "BAD": pd.DataFrame()}
    result = scan_frames(frames)
    assert {r["ticker"] for r in result["results"]} == {"GOOD"}
    assert result["failed"] == [{"ticker": "BAD", "error": "no data"}] or (
        len(result["failed"]) == 1 and result["failed"][0]["ticker"] == "BAD"
    )


def test_short_history_still_scans_with_available_mas():
    """A ticker with only 60 bars has no 200DMA -- field is None, not a crash."""
    frames = {"YOUNG": _frame(n=60)}
    result = scan_frames(frames)
    row = result["results"][0]
    assert row["pct_from_200dma"] is None
    assert row["pct_from_20dma"] is not None
