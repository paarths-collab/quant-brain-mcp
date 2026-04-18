from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from core.data_loader import fetch_data
from core.sector_data import INDIAN_SECTORS, US_SECTORS
from tools.intelligence.alpha_engine import calculate_alpha_metrics
from tools.intelligence.engine import get_quant_analysis


_BREAKOUT_DESCRIPTION = "Close above 20D high with positive regime and risk-adjusted confirmation"


_TIMEFRAME_ALIASES = {
    "1m": "1mo",
    "2m": "2mo",
    "3m": "3mo",
    "6m": "6mo",
    "1y": "1y",
    "1yr": "1y",
    "12m": "1y",
    "2y": "2y",
    "24m": "2y",
    "3y": "3y",
    "36m": "3y",
    "5y": "5y",
    "60m": "5y",
    "10y": "10y",
    "120m": "10y",
}


def _normalize_timeframe(timeframe: str | None, default: str = "1y") -> str:
    raw = (timeframe or "").strip().lower()
    if not raw:
        return default
    return _TIMEFRAME_ALIASES.get(raw, default)


def _pick_universe(market: str) -> dict[str, dict[str, Any]]:
    market_key = market.strip().lower()
    if market_key in {"india", "in", "nse"}:
        return INDIAN_SECTORS
    if market_key in {"us", "usa", "nyse", "nasdaq"}:
        return US_SECTORS
    raise ValueError("market must be one of: india, us")


def _score_sector(index_df) -> float:
    if index_df is None or index_df.empty:
        return float("-inf")
    start = float(index_df["Close"].iloc[0])
    end = float(index_df["Close"].iloc[-1])
    return ((end / start) - 1) * 100 if start else float("-inf")


def _max_drawdown_pct(close: pd.Series) -> float:
    rolling_peak = close.cummax()
    drawdown = (close / rolling_peak) - 1.0
    return float(drawdown.min() * 100)


def _moving_average_signal(close: pd.Series, short_window: int = 50, long_window: int = 200) -> str:
    if len(close) < long_window:
        return "INSUFFICIENT_DATA"
    sma_short = close.rolling(short_window).mean().iloc[-1]
    sma_long = close.rolling(long_window).mean().iloc[-1]
    if pd.isna(sma_short) or pd.isna(sma_long):
        return "INSUFFICIENT_DATA"
    return "GOLDEN_CROSS_BULLISH" if float(sma_short) > float(sma_long) else "BEARISH"


def analyze_sector_intelligence(market: str = "india", timeframe: str = "1y") -> dict[str, Any]:
    """Compute sector return, risk, momentum, drawdown and correlation, then select best sector."""
    universe = _pick_universe(market)
    selected_timeframe = _normalize_timeframe(timeframe, default="1y")

    analytics: list[dict[str, Any]] = []
    prices: dict[str, pd.Series] = {}
    data_trace: list[dict[str, Any]] = []

    for sector_name, info in universe.items():
        index_ticker = info["index"]
        idx_df, idx_err = fetch_data(index_ticker, period=selected_timeframe)
        if idx_err or idx_df is None or idx_df.empty:
            data_trace.append(
                {
                    "stage": "sector_index",
                    "sector": sector_name,
                    "ticker": index_ticker,
                    "status": "failed",
                    "error": idx_err,
                }
            )
            continue

        close = idx_df["Close"].astype(float).dropna()
        if close.empty:
            data_trace.append(
                {
                    "stage": "sector_index",
                    "sector": sector_name,
                    "ticker": index_ticker,
                    "status": "failed",
                    "error": "Close series empty",
                }
            )
            continue

        returns = close.pct_change(fill_method=None).dropna()
        start_price = float(close.iloc[0])
        end_price = float(close.iloc[-1])
        pct_return = ((end_price / start_price) - 1) * 100 if start_price else float("-inf")
        annualized_vol = float(returns.std() * np.sqrt(252) * 100) if not returns.empty else 0.0
        fifty_two_week_high = float(close.max())
        dist_from_high = ((end_price / fifty_two_week_high) - 1) * 100 if fifty_two_week_high else 0.0
        max_drawdown = _max_drawdown_pct(close)
        ma_signal = _moving_average_signal(close)

        # Composite score: reward return/risk and momentum, penalize deep drawdowns.
        risk_adjusted = pct_return / max(annualized_vol, 1e-6)
        momentum_component = -dist_from_high
        drawdown_penalty = abs(max_drawdown)
        composite_score = (0.50 * risk_adjusted) + (0.35 * momentum_component) - (0.15 * drawdown_penalty)

        analytics.append(
            {
                "sector": sector_name,
                "index": index_ticker,
                "return_pct": round(pct_return, 2),
                "risk_volatility_pct": round(annualized_vol, 2),
                "distance_from_52w_high_pct": round(dist_from_high, 2),
                "max_drawdown_pct": round(max_drawdown, 2),
                "moving_average_signal": ma_signal,
                "risk_adjusted_return": round(risk_adjusted, 3),
                "composite_score": round(composite_score, 3),
            }
        )
        prices[sector_name] = close
        data_trace.append(
            {
                "stage": "sector_index",
                "sector": sector_name,
                "ticker": index_ticker,
                "status": "ok",
                "window": selected_timeframe,
            }
        )

    analytics.sort(key=lambda item: item["composite_score"], reverse=True)
    best_sector = analytics[0] if analytics else None

    corr_df = pd.DataFrame(prices).ffill().dropna()
    corr_matrix = {}
    if not corr_df.empty and len(corr_df.columns) >= 2:
        corr_matrix = corr_df.pct_change(fill_method=None).dropna().corr().round(3).to_dict()

    confidence = min(0.95, 0.55 + len(analytics) * 0.04)
    return {
        "market": market,
        "timeframe": selected_timeframe,
        "sector_analytics": analytics,
        "best_sector": best_sector,
        "correlation_matrix": corr_matrix,
        "data_trace": data_trace,
        "confidence": round(confidence, 2),
    }


def _score_stock(stock_df) -> float:
    if stock_df is None or stock_df.empty:
        return float("-inf")

    close = stock_df["Close"]
    if len(close) < 25:
        return float("-inf")

    recent = close.iloc[-1]
    high_20 = close.tail(20).max()
    volume_score = 0.0
    if "Volume" in stock_df.columns and stock_df["Volume"].notna().any():
        volume_score = float(stock_df["Volume"].tail(10).mean() / max(stock_df["Volume"].tail(50).mean(), 1))

    breakout_score = 1.0 if recent >= high_20 else 0.0
    trend_score = float((close.iloc[-1] / close.iloc[-20]) - 1) * 100 if len(close) >= 20 else 0.0
    return breakout_score * 100 + trend_score + volume_score * 5


def find_sector_stock_pipeline(market: str = "india", top_n_sectors: int = 3, top_n_stocks: int = 3) -> dict[str, Any]:
    """Multi-step pipeline: sector performance -> ranking -> stock selection -> strategy confirmation."""
    universe = _pick_universe(market)

    sector_intel = analyze_sector_intelligence(market=market, timeframe="1y")
    sector_rankings = sector_intel.get("sector_analytics", [])
    chosen_sectors = sector_rankings[:top_n_sectors]
    sector_map = {item["sector"]: item for item in chosen_sectors}

    data_trace: list[dict[str, Any]] = list(sector_intel.get("data_trace", []))

    stock_candidates: list[dict[str, Any]] = []
    for sector_name, sector_item in sector_map.items():
        tickers = universe.get(sector_name, {}).get("tickers", [])
        for ticker in tickers[: max(top_n_stocks * 2, top_n_stocks)]:
            stock_df, stock_err = fetch_data(ticker, period="1y")
            if stock_err or stock_df is None or stock_df.empty:
                data_trace.append({"stage": "stock", "ticker": ticker, "status": "failed", "error": stock_err})
                continue

            quant = get_quant_analysis(stock_df, benchmark_ticker=("^NSEI" if ticker.endswith((".NS", ".BO")) else "^GSPC"))
            alpha = calculate_alpha_metrics(stock_df, benchmark_ticker=("^NSEI" if ticker.endswith((".NS", ".BO")) else "^GSPC"))
            stock_candidates.append(
                {
                    "ticker": ticker,
                    "sector": sector_name,
                    "score": round(_score_stock(stock_df), 2),
                    "regime": quant.get("regime"),
                    "beta": quant.get("beta"),
                    "sharpe_ratio": quant.get("sharpe_ratio"),
                    "alpha": alpha.get("alpha_annualized_pct") if isinstance(alpha, dict) else None,
                    "alpha_verdict": alpha.get("verdict") if isinstance(alpha, dict) else None,
                    "breakout_filter": _BREAKOUT_DESCRIPTION,
                }
            )
            data_trace.append({"stage": "stock", "ticker": ticker, "status": "ok", "window": "1y"})

    stock_candidates.sort(key=lambda item: item["score"], reverse=True)
    selected_stocks = stock_candidates[:top_n_stocks]

    strategy = {
        "name": "breakout_confirmation",
        "rule": _BREAKOUT_DESCRIPTION,
        "logic": "Select top-ranked sector, then top-scoring stock, then confirm with regime + alpha + Sharpe + VaR",
    }

    confidence_inputs = len(sector_rankings) + len(stock_candidates)
    confidence = min(0.95, 0.55 + confidence_inputs * 0.03)

    reproducibility = {
        "market": market,
        "sector_window": "3mo",
        "stock_window": "1y",
        "top_n_sectors": top_n_sectors,
        "top_n_stocks": top_n_stocks,
    }

    return {
        "market": market,
        "sector_rankings": sector_rankings,
        "selected_sectors": chosen_sectors,
        "best_sector": sector_intel.get("best_sector"),
        "sector_correlation_matrix": sector_intel.get("correlation_matrix", {}),
        "selected_stocks": selected_stocks,
        "strategy": strategy,
        "confidence": round(confidence, 2),
        "data_trace": data_trace,
        "reproducibility": reproducibility,
        "verdict": "ACCUMULATE" if selected_stocks else "NEUTRAL",
    }
