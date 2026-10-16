"""Provider snapshots with retrieval times, never an unverified live-price claim."""

from __future__ import annotations

from datetime import datetime, timezone
import math

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

    # Provider fields may be NaN, infinity, or malformed even on a successful fetch.
    for field in _FIELDS:
        if field in {"currency", "timezone", "exchange"}:
            continue
        try:
            value = float(raw[field])
            raw[field] = value if math.isfinite(value) and value >= 0 else None
        except (TypeError, ValueError, OverflowError):
            raw[field] = None

    last = raw["lastPrice"]
    prev = raw["previousClose"]
    if last is None or last <= 0:
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


def _needs_nse_fallback(symbol: str) -> bool:
    # Plain equity symbols only: indices (^), FX/futures (=) and already
    # exchange-suffixed symbols are never rewritten.
    return not any(marker in symbol for marker in (".", "^", "="))


def _quote_with_resolution(symbol: str) -> dict:
    """Quote `symbol`, retrying `<symbol>.NS` like the other data tools do.

    Without this, an unsuffixed Indian symbol ("RELIANCE") never priced, so
    price alerts on it could never fire.
    """
    quote = _one_quote(symbol)
    if "error" in quote and _needs_nse_fallback(symbol):
        try:
            fallback = _one_quote(f"{symbol}.NS")
        except Exception:
            fallback = {"error": "fallback failed"}
        if "error" not in fallback:
            return {**fallback, "resolved_ticker": f"{symbol}.NS"}
    return quote


def get_quotes(tickers: list[str]) -> dict:
    """Batched quote snapshot for one or more tickers (US and Indian).

    Results are keyed by the requested symbol; when an unsuffixed symbol only
    resolved on NSE, the quote carries `resolved_ticker`.
    """
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
            quotes[symbol] = _quote_with_resolution(symbol)
        except Exception as exc:
            quotes[symbol] = {"error": f"Quote fetch failed for '{symbol}': {exc}"}

    fetched_at = datetime.now(timezone.utc).isoformat()
    return {
        "quotes": quotes,
        "as_of": fetched_at,
        "fetched_at": fetched_at,
        "market_timestamp": None,
        "freshness_status": "unknown",
        "timestamp_note": "as_of/fetched_at records retrieval time, not the quote observation time. fast_info does not provide a verified market timestamp; freshness is unknown.",
        "data_delay_note": (
            "Prices via Yahoo Finance may be delayed (often around 15 minutes for "
            "Indian exchange feeds), cached, or from a previous session. Actual "
            "delay is not measured here for any exchange. Do not call this a "
            "verified live price or official close; use a timestamped exchange "
            "or broker feed when that is required."
        ),
    }
