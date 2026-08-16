"""Trade plan construction: entry, structural stop, position size, R targets.

This answers the question every indicator dodges: WHAT DO I DO?
Given daily OHLC bars, account equity, and risk tolerance, it produces the
atomic unit of trading -- a sized plan with a stop and an invalidation line.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

SWING_LOOKBACK = 10       # bars for the structural swing low/high
ATR_LENGTH = 14
ATR_STOP_MULT = 2.0       # fallback stop distance in ATRs
MIN_STOP_ATR = 0.75       # a stop closer than this is inside daily noise
MAX_RISK_PCT = 50.0
MIN_HISTORY_BARS = 40


def _currency_for(ticker: str) -> tuple[str, str]:
    if str(ticker).upper().endswith((".NS", ".BO")):
        return "INR", "₹"
    return "USD", "$"


def _atr(df: pd.DataFrame, length: int = ATR_LENGTH) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()


def compute_trade_plan(
    df: pd.DataFrame,
    ticker: str,
    equity: float,
    risk_pct: float = 1.0,
    direction: str = "long",
) -> dict:
    """Build a sized trade plan from daily OHLC history.

    The stop is the tighter of (a) the recent swing low/high and (b) a
    2*ATR stop -- but never closer than 0.75*ATR to the entry, so normal
    daily noise cannot knock the position out immediately.
    Position size = risk budget / stop distance, capped so the position
    value never exceeds equity (no implicit leverage).
    """
    direction = str(direction).strip().lower()
    if direction not in {"long", "short"}:
        return {"error": f"Invalid direction '{direction}'. Use 'long' or 'short'."}
    try:
        equity = float(equity)
        risk_pct = float(risk_pct)
    except (TypeError, ValueError):
        return {"error": "equity and risk_pct must be numbers."}
    if equity <= 0:
        return {"error": "equity must be positive."}
    if not (0 < risk_pct <= MAX_RISK_PCT):
        return {"error": f"risk_pct must be between 0 and {MAX_RISK_PCT} (percent of equity risked)."}

    if df is None or df.empty or len(df) < MIN_HISTORY_BARS:
        return {
            "error": (
                f"Insufficient history for a trade plan: need at least {MIN_HISTORY_BARS} "
                f"daily bars, got {0 if df is None else len(df)}."
            )
        }

    close = float(df["Close"].iloc[-1])
    atr_series = _atr(df)
    atr = float(atr_series.iloc[-1])
    if not math.isfinite(atr) or atr <= 0:
        return {"error": "ATR is undefined for this history (flat or invalid data)."}

    entry = close  # reference entry at last close; a live order would refine this

    if direction == "long":
        swing_stop = float(df["Low"].tail(SWING_LOOKBACK).min())
        atr_stop = entry - ATR_STOP_MULT * atr
        # tighter = the HIGHER of the two (closer to entry), but outside noise
        stop = max(swing_stop, atr_stop)
        stop = min(stop, entry - MIN_STOP_ATR * atr)
        stop_distance = entry - stop
    else:
        swing_stop = float(df["High"].tail(SWING_LOOKBACK).max())
        atr_stop = entry + ATR_STOP_MULT * atr
        stop = min(swing_stop, atr_stop)
        stop = max(stop, entry + MIN_STOP_ATR * atr)
        stop_distance = stop - entry

    if stop_distance <= 0 or not math.isfinite(stop_distance):
        return {"error": "Could not derive a valid stop distance from this history."}

    risk_amount = equity * risk_pct / 100.0
    shares = int(risk_amount // stop_distance)

    note = None
    size_capped_by_equity = False
    max_affordable = int(equity // entry)
    if shares > max_affordable:
        shares = max_affordable
        size_capped_by_equity = True
        note = (
            "Position size capped by equity (no leverage assumed); actual risk is "
            "below the requested risk_pct."
        )

    currency, symbol = _currency_for(ticker)

    if shares <= 0:
        return {
            "error": (
                f"Cannot size this trade: one share at {symbol}{entry:,.2f} with a "
                f"{symbol}{stop_distance:,.2f} stop distance exceeds the "
                f"{symbol}{risk_amount:,.2f} risk budget ({risk_pct}% of equity). "
                "Increase equity/risk_pct or pick a lower-priced/lower-volatility name."
            ),
            "ticker": str(ticker).upper(),
            "entry": round(entry, 2),
            "stop": round(stop, 2),
            "stop_distance": round(stop_distance, 2),
            "risk_budget": round(risk_amount, 2),
        }

    # Round once, then derive every dependent number from the ROUNDED values so
    # the plan is internally consistent when a user re-checks the arithmetic.
    stop_distance = round(stop_distance, 2)

    sign = 1 if direction == "long" else -1
    targets = {
        f"{k}R": round(entry + sign * k * stop_distance, 2) for k in (1, 2, 3)
    }

    turnover_20d = float((df["Close"] * df["Volume"]).tail(20).mean())
    order_value = shares * entry
    order_pct = (order_value / turnover_20d * 100) if turnover_20d > 0 else None

    side_word = "below" if direction == "long" else "above"
    plan = {
        "ticker": str(ticker).upper(),
        "direction": direction,
        "as_of": str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1]),
        "currency": currency,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "stop_basis": "swing" if (direction == "long" and stop == swing_stop) or (direction == "short" and stop == swing_stop) else "atr",
        "stop_distance": stop_distance,
        "stop_distance_atr": round(stop_distance / atr, 2),
        "atr_14": round(atr, 2),
        "shares": shares,
        "position_value": round(order_value, 2),
        "position_pct_of_equity": round(order_value / equity * 100, 1),
        "max_loss": round(shares * stop_distance, 2),
        "risk_budget": round(risk_amount, 2),
        "targets": targets,
        "invalidation": (
            f"Thesis invalid {side_word} {symbol}{round(stop, 2)} -- exit without debate."
        ),
        "liquidity": {
            "avg_daily_turnover_20d": round(turnover_20d, 0),
            "order_value": round(order_value, 2),
            "order_pct_of_daily_turnover": round(order_pct, 3) if order_pct is not None else None,
            "note": "Orders above ~1% of daily turnover may move the price." if order_pct and order_pct > 1 else None,
        },
        "size_capped_by_equity": size_capped_by_equity,
        "note": note,
        "disclaimer": (
            "Educational analysis from delayed end-of-day data, not investment advice. "
            "Entry references the last close; verify the live price before ordering."
        ),
    }
    return plan
