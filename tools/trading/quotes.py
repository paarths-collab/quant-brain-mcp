"""Delayed-quote snapshots via yfinance fast_info.

Data honesty: Yahoo quotes are near-real-time for US exchanges but ~15
minutes delayed for NSE/BSE. Every response carries an `as_of` timestamp and
an explicit delay note -- traders forgive disclosed delay, never undisclosed
staleness.
"""

from __future__ import annotations

from datetime import datetime, timezone

import yfinance as yf

_FIELDS = (
    "lastPrice",
    "previousClose",
    "dayHigh",
    "dayLow",
    "yearHigh",
    "yearLow",
    "lastVolume",
    "threeMonthAverageVolume",
    "currency",
    "timezone",
    "exchange",
)


def _one_quote(symbol: str) -> dict:
    info = yf.Ticker(symbol).fast_info
    raw = {}
    for field in _FIELDS:
        try:
            raw[field] = info[field]
        except Exception:
            raw[field] = None

    last = raw["lastPrice"]
    prev = raw["previousClose"]
    if last is None:
        return {"error": f"No quote data available for '{symbol}'."}

    day_change_pct = None
    if prev:
        day_change_pct = round((float(last) / float(prev) - 1) * 100, 2)

    year_low, year_high = raw["yearLow"], raw["yearHigh"]
    pct_of_52w_range = None
    if year_low is not None and year_high is not None and year_high > year_low:
        pct_of_52w_range = round(
            (float(last) - float(year_low)) / (float(year_high) - float(year_low)) * 100, 1
        )

    volume = raw["lastVolume"]
    avg_volume = raw["threeMonthAverageVolume"]
    volume_vs_avg = None
    if volume is not None and avg_volume:
        volume_vs_avg = round(float(volume) / float(avg_volume), 2)

    return {
        "last_price": round(float(last), 2),
        "previous_close": round(float(prev), 2) if prev is not None else None,
        "day_change_pct": day_change_pct,
        "day_range": {
            "low": round(float(raw["dayLow"]), 2) if raw["dayLow"] is not None else None,
            "high": round(float(raw["dayHigh"]), 2) if raw["dayHigh"] is not None else None,
        },
        "52w_range": {
            "low": round(float(year_low), 2) if year_low is not None else None,
            "high": round(float(year_high), 2) if year_high is not None else None,
        },
        "pct_of_52w_range": pct_of_52w_range,
        "volume": int(volume) if volume is not None else None,
        "volume_vs_3mo_avg": volume_vs_avg,
        "currency": raw["currency"],
        "exchange": raw["exchange"],
        "exchange_timezone": raw["timezone"],
    }


def get_quotes(tickers: list[str]) -> dict:
    """Batched quote snapshot for one or more tickers (US and Indian)."""
    if not tickers:
        return {"error": "Provide at least one ticker symbol."}

    normalized: list[str] = []
    for t in tickers:
        symbol = str(t).strip().upper()
        if symbol and symbol not in normalized:
            normalized.append(symbol)

    quotes: dict[str, dict] = {}
    for symbol in normalized:
        try:
            quotes[symbol] = _one_quote(symbol)
        except Exception as exc:
            quotes[symbol] = {"error": f"Quote fetch failed for '{symbol}': {exc}"}

    return {
        "quotes": quotes,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "data_delay_note": (
            "Prices via Yahoo Finance: US exchanges are near-real-time; "
            "NSE/BSE quotes are delayed roughly 15 minutes. For to-the-second "
            "Indian prices during market hours, cross-check with a live source."
        ),
    }
