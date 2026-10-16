from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from core.data_loader import VALID_PERIODS, fetch_data
from core.sector_data import INDIAN_SECTORS, US_SECTORS
from tools.intelligence.alpha_engine import calculate_alpha_metrics
from tools.intelligence.engine import get_quant_analysis


_BREAKOUT_DESCRIPTION = "Close above 20D high with positive regime and risk-adjusted confirmation"


# Shorthand accepted in addition to every canonical yfinance period. Every
# alias must map to a period the data loader accepts.
_TIMEFRAME_ALIASES = {
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1yr": "1y",
    "12m": "1y",
    "24m": "2y",
    "60m": "5y",
    "120m": "10y",
}


def _normalize_timeframe(timeframe: str | None, default: str = "1y") -> str:
    """Map a timeframe to a supported period, rejecting anything else.

    Unknown values used to fall back silently to the default, so canonical
    inputs such as "6mo" or "ytd" were analysed as one year without notice.
    """
    raw = (timeframe or "").strip().lower()
    if not raw:
        return default
    if raw in VALID_PERIODS:
        return raw
    if raw in _TIMEFRAME_ALIASES:
        return _TIMEFRAME_ALIASES[raw]
    accepted = sorted(VALID_PERIODS | set(_TIMEFRAME_ALIASES))
    raise ValueError(f"Unsupported timeframe '{timeframe}'. Use one of: {', '.join(accepted)}.")


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
        pct_return = ((end_price / start_price) - 1) * 100 if start_price else float("-inf")
        annualized_vol = float(returns.std() * np.sqrt(252) * 100) if not returns.empty else 0.0
        fifty_two_week_high = float(close.max())
        dist_from_high = ((end_price / fifty_two_week_high) - 1) * 100 if fifty_two_week_high else 0.0
        max_drawdown = _max_drawdown_pct(close)
        ma_signal = _moving_average_signal(close)

        # Raw score components. The composite is computed after the loop, once
        # every sector is known, so each term can be z-scored onto a common scale.
        risk_adjusted = pct_return / max(annualized_vol, 1e-6)
        drawdown_penalty = abs(max_drawdown)

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

    return {
        "market": market,
        "timeframe": selected_timeframe,
        "sector_analytics": analytics,
        "best_sector": best_sector,
        "correlation_matrix": corr_matrix,
        "data_trace": data_trace,
        "data_coverage": {
            "sectors_analyzed": len(analytics),
            "sectors_requested": len(universe),
            "sectors_stale": len(stale_sectors),
        },
        "confidence": None,
        "confidence_basis": (
            "No calibrated confidence is available; rankings are descriptive. "
            "See data_coverage and data_trace for input completeness."
        ),
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


def _is_breakout(stock_df) -> bool:
    close = stock_df["Close"] if stock_df is not None and not stock_df.empty else None
    if close is None or len(close) < 20:
        return False
    return bool(close.iloc[-1] >= close.tail(20).max())


# Confirmation thresholds for the stated breakout strategy.
CONFIRM_MIN_SHARPE = 1.0
CONFIRM_MIN_VAR_PCT = -3.0


def _confirmation(candidate: dict[str, Any]) -> tuple[bool, list[str]]:
    """Apply the strategy's own confirmation rule; return (confirmed, unmet checks)."""
    var_pct = None
    try:
        var_pct = float(str(candidate.get("var_95") or "").replace("%", ""))
    except ValueError:
        pass
    checks = {
        "breakout above 20-day high": candidate.get("breakout") is True,
        "trending regime": candidate.get("regime") == "TRENDING",
        "positive alpha": isinstance(candidate.get("alpha_annualized"), (int, float)) and candidate["alpha_annualized"] > 0,
        f"Sharpe >= {CONFIRM_MIN_SHARPE}": isinstance(candidate.get("sharpe_ratio"), (int, float)) and candidate["sharpe_ratio"] >= CONFIRM_MIN_SHARPE,
        f"95% one-day VaR above {CONFIRM_MIN_VAR_PCT}%": var_pct is not None and var_pct > CONFIRM_MIN_VAR_PCT,
    }
    unmet = [name for name, passed in checks.items() if not passed]
    return not unmet, unmet


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
    for name, value in (("top_n_sectors", top_n_sectors), ("top_n_stocks", top_n_stocks)):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 10:
            raise ValueError(f"{name} must be an integer between 1 and 10")

    sector_intel = analyze_sector_intelligence(market=market, timeframe="1y")
    sector_rankings = sector_intel.get("sector_analytics", [])
    chosen_sectors = sector_rankings[:top_n_sectors]
    sector_map = {item["sector"]: item for item in chosen_sectors}

    data_trace: list[dict[str, Any]] = list(sector_intel.get("data_trace", []))

    # One benchmark download per index, shared by every stock and both analyses.
    benchmarks: dict[str, tuple] = {}

    stock_candidates: list[dict[str, Any]] = []
    for sector_name, sector_item in sector_map.items():
        tickers = universe.get(sector_name, {}).get("tickers", [])
        for ticker in tickers[: top_n_stocks * 2]:
            stock_df, stock_err = fetch_data(ticker, period="1y")
            if stock_err or stock_df is None or stock_df.empty:
                data_trace.append({"stage": "stock", "ticker": ticker, "status": "failed", "error": stock_err})
                continue

            benchmark = "^NSEI" if ticker.endswith((".NS", ".BO")) else "^GSPC"
            if benchmark not in benchmarks:
                benchmarks[benchmark] = fetch_data(benchmark, period="1y")
            bench_df, bench_err = benchmarks[benchmark]

            # A failed benchmark or analysis degrades this one candidate; it
            # must not abort the whole pipeline.
            problems: list[str] = []
            quant: dict[str, Any] = {}
            alpha: dict[str, Any] = {}
            if bench_err or bench_df is None or bench_df.empty:
                problems.append(f"Benchmark data unavailable for {benchmark}: {bench_err}")
            else:
                try:
                    quant = get_quant_analysis(stock_df, benchmark_ticker=benchmark, benchmark_df=bench_df)
                except Exception as exc:
                    problems.append(f"Quant analysis failed: {exc}")
                try:
                    alpha = calculate_alpha_metrics(stock_df, benchmark_ticker=benchmark, bench_df=bench_df)
                except Exception as exc:
                    alpha = {"error": f"Alpha analysis failed: {exc}"}
                if "error" in alpha:
                    problems.append(str(alpha["error"]))
                    alpha = {}

            candidate = {
                "ticker": ticker,
                "sector": sector_name,
                "score": round(_score_stock(stock_df), 2),
                "breakout": _is_breakout(stock_df),
                "regime": quant.get("regime"),
                "beta": quant.get("beta"),
                "sharpe_ratio": quant.get("sharpe_ratio"),
                "var_95": quant.get("one_day_var_95"),
                "alpha": alpha.get("alpha_annualized_pct"),
                "alpha_annualized": alpha.get("alpha_annualized"),
                "alpha_verdict": alpha.get("verdict"),
                "breakout_filter": _BREAKOUT_DESCRIPTION,
            }
            confirmed, unmet = _confirmation(candidate)
            candidate["confirmed"] = confirmed
            candidate["unmet_confirmations"] = unmet
            if problems:
                candidate["analysis_errors"] = problems
            stock_candidates.append(candidate)
            trace = {"stage": "stock", "ticker": ticker, "status": "partial" if problems else "ok", "window": "1y"}
            if problems:
                trace["error"] = "; ".join(problems)
            data_trace.append(trace)

    stock_candidates.sort(key=lambda item: item["score"], reverse=True)
    selected_stocks = stock_candidates[:top_n_stocks]
    confirmed_stocks = [item["ticker"] for item in selected_stocks if item["confirmed"]]

    strategy = {
        "name": "breakout_confirmation",
        "rule": _BREAKOUT_DESCRIPTION,
        "logic": "Select top-ranked sector, then top-scoring stock, then confirm with regime + alpha + Sharpe + VaR",
    }

    reproducibility = {
        "market": market,
        "sector_window": "1y",
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
        "confirmed_stocks": confirmed_stocks,
        "confidence": None,
        "confidence_basis": (
            "No calibrated confidence is available. The verdict reflects only whether a "
            "selected stock met every confirmation check; see unmet_confirmations."
        ),
        "data_trace": data_trace,
        "reproducibility": reproducibility,
        "verdict": "ACCUMULATE" if confirmed_stocks else "NEUTRAL",
    }
