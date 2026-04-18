"""Institutional quant intelligence engine (beta, regime, VaR, Sharpe, ES)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pandas_ta as ta

from core.data_loader import fetch_data


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


def _hurst_exponent(close_series: pd.Series, max_lag: int = 20) -> float | None:
    """Estimate Hurst exponent from close prices.

    Returns None when data is insufficient for a stable estimate.
    """
    series = close_series.dropna().astype(float)
    if len(series) < max_lag + 30:
        return None

    lags = range(2, max_lag)
    tau = []
    for lag in lags:
        diff = series.diff(lag).dropna()
        if diff.empty:
            continue
        std = float(np.std(diff))
        if std <= 0:
            continue
        tau.append(np.sqrt(std))

    if len(tau) < 5:
        return None

    slope = np.polyfit(np.log(list(range(2, 2 + len(tau)))), np.log(tau), 1)[0]
    hurst = float(2.0 * slope)
    return hurst


def _regime_from_hurst_adx(hurst: float | None, adx_val: float | None) -> str:
    if hurst is not None:
        if hurst > 0.55:
            return "TRENDING"
        if hurst < 0.45:
            return "MEAN_REVERTING"
        return "STOCHASTIC"

    if adx_val is None:
        return "UNKNOWN"
    if adx_val > 25:
        return "TRENDING"
    if adx_val < 20:
        return "MEAN_REVERTING"
    return "STOCHASTIC"


def get_quant_analysis(df: pd.DataFrame, benchmark_ticker: str = "^NSEI") -> dict:
    """Institutional-grade analysis for a single asset.

    Metrics:
    - Beta (systematic sensitivity)
    - Hurst Exponent + regime
    - Sharpe ratio (annualized)
    - 1-day VaR and Expected Shortfall at 95%
    """
    required_cols = {"High", "Low", "Close"}
    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns for quant analysis: {sorted(missing)}")

    returns = df["Close"].pct_change(fill_method=None).dropna()
    if returns.empty:
        raise ValueError("Insufficient return history for quant analysis")

    benchmark_df, bench_err = fetch_data(benchmark_ticker, period="2y")
    if bench_err or benchmark_df is None or benchmark_df.empty:
        raise ValueError(f"Benchmark data unavailable for {benchmark_ticker}: {bench_err}")

    combined = pd.DataFrame({
        "asset": df["Close"],
        "benchmark": benchmark_df["Close"],
    }).ffill().pct_change(fill_method=None).dropna()

    if combined.empty:
        raise ValueError("Insufficient overlap with benchmark for beta computation")

    asset_returns = combined["asset"]
    bench_returns = combined["benchmark"]

    covariance = np.cov(asset_returns, bench_returns)[0][1]
    variance = float(np.var(bench_returns))
    beta = float(covariance / variance) if variance > 0 else 0.0

    # ADX proxy supports regime detection when Hurst is noisy.
    adx_df = ta.adx(df["High"], df["Low"], df["Close"], length=14)
    adx_col = _pick_col(adx_df, "ADX_") if adx_df is not None else None
    adx_val = _last_valid(adx_df[adx_col]) if adx_col else None

    hurst = _hurst_exponent(df["Close"])
    regime = _regime_from_hurst_adx(hurst, adx_val)

    var_95 = float(np.percentile(asset_returns, 5))
    tail_losses = asset_returns[asset_returns <= var_95]
    expected_shortfall_95 = float(tail_losses.mean()) if not tail_losses.empty else var_95

    volatility_ann = float(asset_returns.std() * np.sqrt(252))
    sharpe = float((asset_returns.mean() / asset_returns.std()) * np.sqrt(252)) if asset_returns.std() > 0 else 0.0

    alpha_signal = "NEUTRAL"
    if sharpe >= 1.0 and var_95 > -0.03:
        alpha_signal = "ACCUMULATE"
    elif sharpe < 0.2 or var_95 < -0.05:
        alpha_signal = "REDUCE"

    return {
        "benchmark": benchmark_ticker,
        "beta": round(beta, 2),
        "hurst_exponent": None if hurst is None else round(hurst, 3),
        "regime": regime,
        "adx_14": None if adx_val is None else round(adx_val, 2),
        "sharpe_ratio": round(sharpe, 2),
        "one_day_var_95": f"{var_95 * 100:.2f}%",
        "expected_shortfall_95": f"{expected_shortfall_95 * 100:.2f}%",
        "volatility_ann": f"{volatility_ann * 100:.2f}%",
        "institutional_verdict": alpha_signal,
    }


def get_quant_context(df: pd.DataFrame) -> dict:
    """Backward-compatible wrapper for existing call sites.

    This keeps older clients working while using the upgraded quant engine.
    """
    quant = get_quant_analysis(df)
    return {
        "regime": quant["regime"],
        "adx_14": quant["adx_14"],
        "consensus_score": f"Sharpe {quant['sharpe_ratio']}",
        "tail_risk_warning": (
            f"95% one-day VaR: {quant['one_day_var_95']}; "
            f"Expected Shortfall: {quant['expected_shortfall_95']}"
        ),
        "institutional_verdict": quant["institutional_verdict"],
    }
