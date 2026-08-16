"""Tests for bug H12: stale sector indices were silently stamped status: ok.

Live audit: 5 of 8 Indian sector indices (Energy, Automobiles, FMCG, Metals,
Realty) stopped updating at 2026-07-17 while the other 3 (Private Banks, IT
Services, Pharma) ran current to 2026-08-14 -- a 28-day gap -- yet every row
carried "status": "ok" with no way to tell them apart. Rankings silently
compared different windows. TATAMOTORS.NS also 404s live (Tata Motors
demerged; the passenger-vehicle listing is now TMPV.NS).
"""

from unittest.mock import patch

import numpy as np
import pandas as pd

from core.sector_data import INDIAN_SECTORS
from tools.strategies.sector_pipeline import analyze_sector_intelligence


def _close_series(last_date, periods=60, start=1000.0):
    idx = pd.date_range(end=last_date, periods=periods, freq="B")
    rng = np.random.default_rng(hash(str(last_date)) % (2**31))
    close = pd.Series(start * np.exp(np.cumsum(rng.normal(0.0003, 0.01, periods))), index=idx)
    return pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1000}
    )


def test_tata_motors_ticker_is_the_currently_listed_symbol():
    """TATAMOTORS.NS 404s live (Tata Motors demerged); TMPV.NS is the
    passenger-vehicle listing that actually resolves."""
    auto_tickers = INDIAN_SECTORS["Automobiles"]["tickers"]
    assert "TATAMOTORS.NS" not in auto_tickers
    assert "TMPV.NS" in auto_tickers


def test_stale_sector_flagged_not_silently_marked_ok():
    fresh_date = pd.Timestamp("2026-08-14")
    stale_date = pd.Timestamp("2026-07-17")  # 28 days behind, matches the live finding

    def fetch_stub(ticker, period="1y", interval="1d"):
        if ticker == "^NSEBANK":
            return _close_series(fresh_date), None
        if ticker == "^CNXENERGY":
            return _close_series(stale_date), None
        return {"error": "not used in this test"}, "skip"

    universe = {
        "Private Banks": {"index": "^NSEBANK", "tickers": []},
        "Energy": {"index": "^CNXENERGY", "tickers": []},
    }

    with patch("tools.strategies.sector_pipeline.fetch_data", side_effect=lambda t, **kw: fetch_stub(t)), \
         patch("tools.strategies.sector_pipeline._pick_universe", return_value=universe):
        result = analyze_sector_intelligence(market="india", timeframe="1y")

    by_sector = {a["sector"]: a for a in result["sector_analytics"]}
    assert by_sector["Private Banks"]["is_stale"] is False
    assert by_sector["Energy"]["is_stale"] is True
    assert by_sector["Energy"]["days_behind_freshest"] == 28

    assert result["stale_sectors"] == ["Energy"]
    assert result["data_freshness_note"] is not None

    trace_by_sector = {t["sector"]: t for t in result["data_trace"]}
    assert trace_by_sector["Energy"]["status"] == "stale"
    assert trace_by_sector["Private Banks"]["status"] == "ok"


def test_all_sectors_equally_fresh_has_no_stale_flags():
    """Regression: no false positives when every sector is on the same date."""
    same_date = pd.Timestamp("2026-08-14")

    def fetch_stub(t, **kw):
        return _close_series(same_date), None

    universe = {
        "A": {"index": "^A", "tickers": []},
        "B": {"index": "^B", "tickers": []},
    }

    with patch("tools.strategies.sector_pipeline.fetch_data", side_effect=fetch_stub), \
         patch("tools.strategies.sector_pipeline._pick_universe", return_value=universe):
        result = analyze_sector_intelligence(market="india", timeframe="1y")

    assert result["stale_sectors"] == []
    assert result["data_freshness_note"] is None
    for entry in result["sector_analytics"]:
        assert entry["is_stale"] is False
        assert entry["days_behind_freshest"] == 0


def test_small_gap_within_tolerance_is_not_flagged_stale():
    """A 1-2 day gap (e.g. different holiday calendars) should not be flagged;
    only a meaningfully stale feed should be."""
    fresh_date = pd.Timestamp("2026-08-14")
    almost_fresh = pd.Timestamp("2026-08-13")

    def fetch_stub(ticker, **kw):
        return _close_series(fresh_date if ticker == "^A" else almost_fresh), None

    universe = {"A": {"index": "^A", "tickers": []}, "B": {"index": "^B", "tickers": []}}

    with patch("tools.strategies.sector_pipeline.fetch_data", side_effect=fetch_stub), \
         patch("tools.strategies.sector_pipeline._pick_universe", return_value=universe):
        result = analyze_sector_intelligence(market="india", timeframe="1y")

    for entry in result["sector_analytics"]:
        assert entry["is_stale"] is False
