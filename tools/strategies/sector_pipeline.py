from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from core.data_loader import fetch_data
from core.risk_state import finite, is_unavailable, unavailable
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


SCORE_WEIGHTS = {"risk_adjusted": 0.50, "momentum": 0.35, "drawdown": 0.15}


def _zscores(values: list[float]) -> list[float]:
    """Standardize to mean 0 / std 1. Returns zeros when there is no spread."""
    if not values:
        return []
    arr = np.asarray(values, dtype=float)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    std = float(arr.std())
    if std < 1e-12:
        return [0.0] * len(values)
    return ((arr - float(arr.mean())) / std).tolist()


def _apply_composite_scores(analytics: list[dict[str, Any]]) -> None:
    """Compute each sector's composite score from z-scored components, in place.

    Every term is standardized across the sector cross-section before weighting.
    Without this, raw units dominate: momentum runs on the order of +/-40 (percent)
    while risk_adjusted is roughly +/-2, so the 0.50 weight on risk_adjusted was
    swamped regardless of intent.

    Momentum is the period return. It was previously `-dist_from_high`, which is
    non-negative by construction and therefore *rewarded* sectors for trading
    further below their 52-week high -- inverting the intended signal.
    """
    if not analytics:
        return

    z_risk = _zscores([item["_risk_adjusted_raw"] for item in analytics])
    z_momentum = _zscores([item["_momentum_raw"] for item in analytics])
    z_drawdown = _zscores([item["_drawdown_raw"] for item in analytics])

    for item, zr, zm, zd in zip(analytics, z_risk, z_momentum, z_drawdown):
        score = (
            SCORE_WEIGHTS["risk_adjusted"] * zr
            + SCORE_WEIGHTS["momentum"] * zm
            - SCORE_WEIGHTS["drawdown"] * zd
        )
        item["composite_score"] = round(score, 3)
        item["score_components"] = {
            "risk_adjusted_z": round(zr, 3),
            "momentum_z": round(zm, 3),
            "drawdown_z": round(zd, 3),
        }
        for key in ("_risk_adjusted_raw", "_momentum_raw", "_drawdown_raw"):
            item.pop(key, None)


# A sector index feed more than this many calendar days behind the freshest
# fetched index is flagged stale rather than silently stamped "ok". Live audit
# found 5 of 8 Indian sector indices stuck 28 days behind the other 3, with
# every row stamped "status": "ok" and no way to tell them apart -- rankings
# silently compared mismatched windows.
STALE_AFTER_DAYS = 5


def analyze_sector_intelligence(market: str = "india", timeframe: str = "1y") -> dict[str, Any]:
    """Compute sector return, risk, momentum, drawdown and correlation, then select best sector."""
    universe = _pick_universe(market)
    selected_timeframe = _normalize_timeframe(timeframe, default="1y")

    analytics: list[dict[str, Any]] = []
    unranked: list[dict[str, Any]] = []
    prices: dict[str, pd.Series] = {}
    data_trace: list[dict[str, Any]] = []
    trace_by_sector: dict[str, dict[str, Any]] = {}

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
        pct_return = ((end_price / start_price) - 1) * 100 if start_price else float("nan")
        annualized_vol = float(returns.std() * np.sqrt(252) * 100) if len(returns) > 1 else float("nan")

        # A sector whose risk cannot be computed is reported as unranked with a
        # reason. Scoring it would publish vol=0 as a measured risk (and, for a
        # rising index, divide by 1e-6 for an enormous risk-adjusted score);
        # z-scoring a NaN as 0 would rank it as exactly average.
        risk_problem = None
        if not finite(pct_return):
            risk_problem = "Index start price is zero; return is undefined"
        elif not finite(annualized_vol):
            risk_problem = "Fewer than three price observations; volatility is undefined"
        elif annualized_vol <= 0:
            risk_problem = "Index has no return variance; risk-adjusted return is undefined"
        if risk_problem:
            unranked.append({"sector": sector_name, "index": index_ticker, **unavailable(risk_problem),
                             "risk_status": "unavailable"})
            data_trace.append({"stage": "sector_index", "sector": sector_name, "ticker": index_ticker,
                               "status": "risk_unavailable", "error": risk_problem})
            continue

        fifty_two_week_high = float(close.max())
        dist_from_high = ((end_price / fifty_two_week_high) - 1) * 100 if fifty_two_week_high else 0.0
        max_drawdown = _max_drawdown_pct(close)
        ma_signal = _moving_average_signal(close)

        # Raw score components. The composite is computed after the loop, once
        # every sector is known, so each term can be z-scored onto a common scale.
        risk_adjusted = pct_return / annualized_vol
        drawdown_penalty = abs(max_drawdown)

        analytics.append(
            {
                "sector": sector_name,
                "index": index_ticker,
                "risk_status": "available",
                "return_pct": round(pct_return, 2),
                "risk_volatility_pct": round(annualized_vol, 2),
                "distance_from_52w_high_pct": round(dist_from_high, 2),
                "max_drawdown_pct": round(max_drawdown, 2),
                "moving_average_signal": ma_signal,
                "risk_adjusted_return": round(risk_adjusted, 3),
                "_risk_adjusted_raw": risk_adjusted,
                "_momentum_raw": pct_return,
                "_drawdown_raw": drawdown_penalty,
                "_last_date": close.index[-1],
            }
        )
        prices[sector_name] = close
        trace_entry = {
            "stage": "sector_index",
            "sector": sector_name,
            "ticker": index_ticker,
            "status": "ok",
            "window": selected_timeframe,
        }
        data_trace.append(trace_entry)
        trace_by_sector[sector_name] = trace_entry

    stale_sectors: list[str] = []
    if analytics:
        freshest_date = max(item["_last_date"] for item in analytics)
        for item in analytics:
            last_date = item.pop("_last_date")
            days_behind = (freshest_date - last_date).days
            is_stale = days_behind > STALE_AFTER_DAYS
            item["last_observed_date"] = last_date.strftime("%Y-%m-%d")
            item["days_behind_freshest"] = days_behind
            item["is_stale"] = is_stale
            if is_stale:
                stale_sectors.append(item["sector"])
                trace = trace_by_sector.get(item["sector"])
                if trace is not None:
                    trace["status"] = "stale"
                    trace["days_behind_freshest"] = days_behind

    _apply_composite_scores(analytics)
    analytics.sort(key=lambda item: item["composite_score"], reverse=True)
    best_sector = analytics[0] if analytics else None

    corr_df = pd.DataFrame(prices).ffill().dropna()
    corr_matrix = {}
    if not corr_df.empty and len(corr_df.columns) >= 2:
        corr_matrix = corr_df.pct_change(fill_method=None).dropna().corr().round(3).to_dict()

    attempted = len(universe)
    failed = sum(1 for row in data_trace if row.get("status") == "failed")
    coverage = {
        "attempted": attempted,
        "ranked": len(analytics),
        "failed": failed,
        "risk_unavailable": len(unranked),
        # Failed and unscorable sectors stay in the denominator.
        "coverage": round(len(analytics) / attempted, 4) if attempted else None,
    }
    confidence = min(0.95, 0.55 + len(analytics) * 0.04)
    if coverage["coverage"] is not None:
        confidence *= coverage["coverage"]
    return {
        "market": market,
        "timeframe": selected_timeframe,
        "sector_analytics": analytics,
        "unranked_sectors": unranked,
        "coverage": coverage,
        "best_sector": best_sector,
        "correlation_matrix": corr_matrix,
        "data_trace": data_trace,
        "confidence": round(confidence, 2),
        "stale_sectors": stale_sectors,
        "data_freshness_note": (
            f"{len(stale_sectors)} of {len(analytics)} sector indices are more than "
            f"{STALE_AFTER_DAYS} days behind the freshest fetched index "
            f"({', '.join(stale_sectors)}); rankings may compare mismatched windows "
            "for those sectors."
        )
        if stale_sectors
        else None,
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

            benchmark = "^NSEI" if ticker.endswith((".NS", ".BO")) else "^GSPC"
            try:
                quant = get_quant_analysis(stock_df, benchmark_ticker=benchmark)
            except Exception as exc:
                quant = unavailable(str(exc))
            try:
                alpha = calculate_alpha_metrics(stock_df, benchmark_ticker=benchmark)
            except Exception as exc:
                alpha = unavailable(str(exc))

            reason = None
            if is_unavailable(quant):
                reason = quant["reason"]
            elif is_unavailable(alpha):
                reason = alpha["reason"]
            candidate = {
                "ticker": ticker,
                "sector": sector_name,
                "score": round(_score_stock(stock_df), 2),
                "risk_status": "available" if reason is None else "unavailable",
                "regime": quant.get("regime"),
                "beta": quant.get("beta"),
                "sharpe_ratio": quant.get("sharpe_ratio"),
                "alpha": alpha.get("alpha_annualized_pct"),
                "alpha_verdict": alpha.get("verdict"),
                "breakout_filter": _BREAKOUT_DESCRIPTION,
            }
            if reason is not None:
                candidate["reason"] = reason
            stock_candidates.append(candidate)
            data_trace.append({
                "stage": "stock", "ticker": ticker,
                "status": "ok" if reason is None else "risk_unavailable", "window": "1y",
                **({"error": reason} if reason is not None else {}),
            })

    # The strategy confirms a breakout with regime + alpha + Sharpe + VaR. A
    # candidate whose risk could not be computed is unconfirmed, not neutral, so
    # it cannot be selected.
    confirmable = [c for c in stock_candidates if c["risk_status"] == "available"]
    unconfirmed_stocks = [c for c in stock_candidates if c["risk_status"] != "available"]
    confirmable.sort(key=lambda item: item["score"], reverse=True)
    selected_stocks = confirmable[:top_n_stocks]
    stock_attempts = [row for row in data_trace if row.get("stage") == "stock"]
    stock_coverage = {
        "attempted": len(stock_attempts),
        "confirmed": len(confirmable),
        "failed": sum(1 for row in stock_attempts if row["status"] == "failed"),
        "risk_unavailable": len(unconfirmed_stocks),
        "coverage": round(len(confirmable) / len(stock_attempts), 4) if stock_attempts else None,
    }

    strategy = {
        "name": "breakout_confirmation",
        "rule": _BREAKOUT_DESCRIPTION,
        "logic": "Select top-ranked sector, then top-scoring stock, then confirm with regime + alpha + Sharpe + VaR",
    }

    confidence_inputs = len(sector_rankings) + len(confirmable)
    confidence = min(0.95, 0.55 + confidence_inputs * 0.03)
    for part in (sector_intel.get("coverage", {}), stock_coverage):
        if part.get("coverage") is not None:
            confidence *= part["coverage"]

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
        "unconfirmed_stocks": unconfirmed_stocks,
        "coverage": {"sectors": sector_intel.get("coverage"), "stocks": stock_coverage},
        "strategy": strategy,
        "confidence": round(confidence, 2),
        "data_trace": data_trace,
        "reproducibility": reproducibility,
        "verdict": "ACCUMULATE" if selected_stocks else "NEUTRAL",
    }
