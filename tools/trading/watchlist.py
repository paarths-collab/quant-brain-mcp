"""Watchlist scanner: one call, every name's actionable state.

The weekly-habit tool: a trader runs this over their list every Sunday and
sees which names actually did something -- crossed a moving average, spiked
volume, approached a 52-week high, gapped -- sorted most-actionable first.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

MIN_BARS = 25
NEAR_HIGH_PCT = -2.0        # within 2% of the 52w high
VOLUME_SPIKE_MULT = 2.0     # last volume > 2x its 20d average
GAP_ATR_MULT = 1.0          # open gapped more than 1 ATR from prior close


def _pct_from(close: float, level: float | None) -> float | None:
    if level is None or not math.isfinite(level) or level == 0:
        return None
    return round((close / level - 1) * 100, 2)


def _last_ma(close: pd.Series, length: int) -> float | None:
    if len(close) < length:
        return None
    value = float(close.rolling(length).mean().iloc[-1])
    return value if math.isfinite(value) else None


def _atr_pct(df: pd.DataFrame, length: int = 14) -> float | None:
    if len(df) < length + 1:
        return None
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = float(tr.ewm(alpha=1 / length, min_periods=length, adjust=False).mean().iloc[-1])
    last = float(close.iloc[-1])
    if not math.isfinite(atr) or last == 0:
        return None
    return round(atr / last * 100, 2)


def _scan_one(ticker: str, df: pd.DataFrame) -> dict:
    close = df["Close"].astype(float)
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    as_of = df.index[-1]

    ma20 = _last_ma(close, 20)
    ma50 = _last_ma(close, 50)
    ma200 = _last_ma(close, 200)

    year = close.tail(252)
    high_52w = float(year.max())

    vol = df["Volume"].astype(float)
    vol_avg_20 = float(vol.tail(21).iloc[:-1].mean()) if len(vol) > 21 else float(vol.mean())
    vol_ratio = round(float(vol.iloc[-1]) / vol_avg_20, 2) if vol_avg_20 > 0 else None

    atr_pct = _atr_pct(df)
    open_last = float(df["Open"].iloc[-1])
    gap_pct = round((open_last / prev - 1) * 100, 2) if prev else None
    gap_in_atr = (
        round(abs(open_last - prev) / (atr_pct / 100 * last), 2)
        if atr_pct and last
        else None
    )

    row = {
        "ticker": ticker,
        "as_of": str(as_of.date()) if hasattr(as_of, "date") else str(as_of),
        "last_close": round(last, 2),
        "day_change_pct": round((last / prev - 1) * 100, 2) if prev else None,
        "gap_pct": gap_pct,
        "pct_from_20dma": _pct_from(last, ma20),
        "pct_from_50dma": _pct_from(last, ma50),
        "pct_from_200dma": _pct_from(last, ma200),
        "pct_from_52w_high": _pct_from(last, high_52w),
        "atr_pct": atr_pct,
        "volume_vs_20d_avg": vol_ratio,
    }

    rules: list[str] = []
    if row["pct_from_52w_high"] is not None and row["pct_from_52w_high"] >= NEAR_HIGH_PCT:
        rules.append("near_52w_high")
    if vol_ratio is not None and vol_ratio >= VOLUME_SPIKE_MULT:
        rules.append("volume_spike")
    if row["pct_from_200dma"] is not None:
        prev_vs_ma200 = _pct_from(prev, ma200)
        if prev_vs_ma200 is not None and prev_vs_ma200 < 0 <= row["pct_from_200dma"]:
            rules.append("crossed_above_200dma")
        elif prev_vs_ma200 is not None and prev_vs_ma200 >= 0 > row["pct_from_200dma"]:
            rules.append("crossed_below_200dma")
    if row["pct_from_20dma"] is not None and abs(row["pct_from_20dma"]) <= 1.0:
        rules.append("at_20dma")
    if gap_in_atr is not None and gap_in_atr >= GAP_ATR_MULT:
        rules.append("gapped_over_1atr")

    row["rules_fired"] = rules
    return row


def scan_frames(frames: dict[str, pd.DataFrame]) -> dict:
    """Scan pre-fetched OHLC frames. Pure function; fetching happens upstream."""
    results = []
    failed = []
    for ticker, df in frames.items():
        if df is None or df.empty or len(df) < MIN_BARS or "Close" not in getattr(df, "columns", []):
            failed.append({"ticker": ticker, "error": "no data"})
            continue
        try:
            results.append(_scan_one(ticker, df))
        except Exception as exc:
            failed.append({"ticker": ticker, "error": str(exc)})

    results.sort(key=lambda r: len(r["rules_fired"]), reverse=True)
    return {
        "results": results,
        "failed": failed,
        "rules_checked": [
            "near_52w_high", "volume_spike", "crossed_above_200dma",
            "crossed_below_200dma", "at_20dma", "gapped_over_1atr",
        ],
    }


def scan_watchlist(tickers: list[str], period: str = "1y") -> dict:
    """Fetch each ticker (with .NS resolution) and scan. Entry point for MCP."""
    from core.data_loader import resolve_ticker

    frames: dict[str, pd.DataFrame] = {}
    failed: list[dict] = []
    seen: set[str] = set()
    for raw in tickers:
        df, err, resolved = resolve_ticker(str(raw), period=period)
        if resolved in seen:
            continue
        seen.add(resolved)
        if err or df is None or df.empty:
            failed.append({"ticker": resolved, "error": err or "no data"})
        else:
            frames[resolved] = df

    out = scan_frames(frames)
    out["failed"] = failed + out["failed"]
    out["period"] = period
    out["disclaimer"] = "End-of-day data (delayed); not investment advice."
    return out
