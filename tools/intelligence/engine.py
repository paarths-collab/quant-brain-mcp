from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def _last_valid(series_or_df: pd.Series | pd.DataFrame | None) -> float | None:
    """Return the latest non-null scalar value from a Series/DataFrame."""
    if series_or_df is None:
        return None

    if isinstance(series_or_df, pd.DataFrame):
        if series_or_df.empty:
            return None
        series = series_or_df.iloc[:, 0]
    else:
        series = series_or_df

    cleaned = series.dropna()
    if cleaned.empty:
        return None

    return float(cleaned.iloc[-1])


def _pick_col(df: pd.DataFrame, prefix: str) -> str | None:
    for col in df.columns:
        if col.startswith(prefix):
            return col
    return None


def get_quant_context(df: pd.DataFrame) -> dict:
    """Build a compact market intelligence summary from core indicators.

    Expects a DataFrame with at least: High, Low, Close.
    """
    required_cols = {"High", "Low", "Close"}
    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns for intelligence engine: {sorted(missing)}")

    # 1) Market regime via ADX
    adx_df = ta.adx(df["High"], df["Low"], df["Close"], length=14)
    adx_col = _pick_col(adx_df, "ADX_") if adx_df is not None else None
    adx_val = _last_valid(adx_df[adx_col]) if adx_col else None

    if adx_val is None:
        regime = "UNKNOWN (Insufficient data for ADX regime detection)"
    elif adx_val > 25:
        regime = "TRENDING (Momentum strategy favored)"
    elif adx_val < 20:
        regime = "RANGING (Mean reversion strategy favored)"
    else:
        regime = "CHOPPY/TRANSITIONAL (Higher whipsaw risk)"

    # 2) Cross-indicator consensus voting
    rsi_series = ta.rsi(df["Close"], length=14)
    rsi_val = _last_valid(rsi_series)

    macd_df = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    macd_col = _pick_col(macd_df, "MACD_") if macd_df is not None else None
    macds_col = _pick_col(macd_df, "MACDs_") if macd_df is not None else None
    macd_val = _last_valid(macd_df[macd_col]) if macd_col else None
    macd_sig = _last_valid(macd_df[macds_col]) if macds_col else None

    ema200_series = ta.ema(df["Close"], length=200)
    ema200_val = _last_valid(ema200_series)
    close_val = _last_valid(df["Close"])

    votes = []

    if rsi_val is not None:
        votes.append(1 if rsi_val < 40 else (-1 if rsi_val > 60 else 0))

    if macd_val is not None and macd_sig is not None:
        votes.append(1 if macd_val > macd_sig else -1)

    if close_val is not None and ema200_val is not None:
        votes.append(1 if close_val > ema200_val else -1)

    if votes:
        bullish_weight = (votes.count(1) / len(votes)) * 100
    else:
        bullish_weight = 0.0

    # 3) Tail risk via historical VaR(95)
    returns = df["Close"].pct_change().dropna()
    var_95 = float(returns.quantile(0.05) * 100) if not returns.empty else 0.0

    institutional_verdict = "ACCUMULATE" if bullish_weight > 60 and (adx_val or 0) > 20 else "AVOID/HEDGE"

    return {
        "regime": regime,
        "adx_14": None if adx_val is None else round(adx_val, 2),
        "consensus_score": f"{bullish_weight:.1f}% Bullish Agreement",
        "tail_risk_warning": (
            f"95% confidence that daily loss should not exceed {abs(var_95):.2f}% "
            "based on observed history."
        ),
        "institutional_verdict": institutional_verdict,
    }
