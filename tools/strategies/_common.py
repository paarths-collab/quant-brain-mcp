"""Shared guards and formatting for the vectorbt strategy backtests."""

from __future__ import annotations

import math


def pct(value) -> str | None:
    """Format a vectorbt percent stat. Undefined values (NaN when no trades
    closed) become None, never the string "nan%"."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return f"{number:.2f}%" if math.isfinite(number) else None


def ratio(value, digits: int = 2) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if math.isfinite(number) else None


def positive_int(name: str, value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer, got {value!r}.")
    return value


def history_error(close, bars: int, strategy: str) -> dict | None:
    """Error payload when the series cannot cover the indicator warm-up.

    Without this guard, too-short history produced a confident-looking
    "0.00% return, 0 trades" result instead of saying the strategy never ran.
    """
    available = int(close.dropna().shape[0])
    if available < bars:
        return {
            "error": (
                f"Insufficient history for {strategy}: need at least {bars} bars for the "
                f"indicator warm-up, got {available}. Request a longer period."
            )
        }
    return None
