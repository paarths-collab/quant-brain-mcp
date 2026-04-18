"""Institutional alpha/beta regression tools for benchmark-relative analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.data_loader import fetch_data


def calculate_alpha_metrics(stock_df: pd.DataFrame, benchmark_ticker: str = "^NSEI") -> dict:
    """Institutional alpha/beta decomposition against a benchmark index.

    Alpha = annualized stock return - beta * annualized benchmark return
    """
    if "Close" not in stock_df.columns:
        raise ValueError("Stock dataframe must contain a 'Close' column")

    bench_df, err = fetch_data(benchmark_ticker, period="2y")
    if err or bench_df is None or bench_df.empty:
        return {"error": f"Benchmark data unavailable for {benchmark_ticker}: {err}"}

    combined = pd.DataFrame(
        {
            "stock": stock_df["Close"],
            "bench": bench_df["Close"],
        }
    ).ffill().pct_change(fill_method=None).dropna()

    if combined.empty or len(combined) < 40:
        return {"error": "Insufficient overlap with benchmark for alpha calculation"}

    matrix = np.cov(combined["stock"], combined["bench"])
    bench_var = float(matrix[1, 1])
    beta = float(matrix[0, 1] / bench_var) if bench_var > 0 else 0.0

    stock_ann_ret = float(combined["stock"].mean() * 252)
    bench_ann_ret = float(combined["bench"].mean() * 252)
    alpha = float(stock_ann_ret - (beta * bench_ann_ret))

    correlation = float(combined["stock"].corr(combined["bench"]))
    r_squared = float(correlation**2)
    outperf_prob = float((combined["stock"] > combined["bench"]).mean())

    verdict = "ALPHA_GENERATOR" if alpha > 0.05 else "BETA_TRACKER"

    return {
        "benchmark": benchmark_ticker,
        "alpha_annualized": round(alpha, 4),
        "alpha_annualized_pct": f"{alpha * 100:.2f}%",
        "beta": round(beta, 2),
        "r_squared": round(r_squared, 2),
        "benchmark_correlation": round(correlation, 2),
        "outperformance_probability": round(outperf_prob, 4),
        "outperformance_probability_pct": f"{outperf_prob * 100:.1f}%",
        "verdict": verdict,
    }


def get_alpha_analysis(df: pd.DataFrame, benchmark_ticker: str = "^NSEI") -> dict:
    """Tool entrypoint: returns institutional alpha/beta regression metrics."""
    return calculate_alpha_metrics(df, benchmark_ticker=benchmark_ticker)
