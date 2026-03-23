"""
Bloomberg Quant Platform - Architecture-Aligned KPI Suite
==========================================================

Purpose:
- Generate resume-ready KPIs using CURRENT backend architecture components.
- Use backend strategy registry + backend backtest engine (run_backtest_on_df).
- Run long sweeps safely with checkpointing and per-task failure isolation.

How to run:
    python bloomberg_kpi_test.py

Quick smoke run:
    python bloomberg_kpi_test.py --dry-run --max-tickers 2

Resume interrupted run:
    python bloomberg_kpi_test.py --resume
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
import time
import traceback
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")

# Ensure project root is importable for `backend.*` package imports.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def _preflight_imports() -> Tuple[Any, Any]:
    required = [
        "numpy",
        "pandas",
        "yfinance",
        "httpx",
    ]
    missing = []
    for module in required:
        if importlib.util.find_spec(module) is None:
            missing.append(module)

    if missing:
        print("Missing Python packages:", ", ".join(missing))
        print("Install with:")
        print("  pip install numpy pandas yfinance httpx")
        raise SystemExit(1)

    import numpy as np  # noqa: WPS433
    import pandas as pd  # noqa: WPS433
    return np, pd


np, pd = _preflight_imports()

try:
    from backend.engine.confidence_engine import calculate_confidence
    from backend.quant.regime_detector import RegimeDetector as BackendRegimeDetector
    from backend.quant.rl_strategy_selector import RLStrategySelector as BackendRLStrategySelector
    from backend.services.backtest_service import run_backtest_on_df
    from backend.services.data_loader import get_history
    from backend.services.strategies.strategy_adapter import STRATEGY_REGISTRY, get_strategy
except Exception as exc:  # pragma: no cover - import guard
    print("Failed importing backend modules. Run from repo root and ensure dependencies are installed.")
    print(f"Import error: {exc}")
    raise SystemExit(1)

print("Backend modules loaded successfully.")


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

NIFTY_50_TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS",
    "HINDUNILVR.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "ITC.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "AXISBANK.NS",
    "ASIANPAINT.NS",
    "MARUTI.NS",
    "WIPRO.NS",
    "ULTRACEMCO.NS",
    "TITAN.NS",
    "BAJFINANCE.NS",
    "NESTLEIND.NS",
    "POWERGRID.NS",
]

SP500_TICKERS = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "META",
    "TSLA",
    "BRK-B",
    "UNH",
    "JPM",
    "V",
    "JNJ",
    "XOM",
    "PG",
    "MA",
    "HD",
    "CVX",
    "MRK",
    "ABBV",
    "PEP",
]

BENCHMARKS = {
    "NIFTY50": "^NSEI",
    "SP500": "^GSPC",
}

TRAIN_START = "2018-01-01"
TRAIN_END = "2022-12-31"
TEST_START = "2023-01-01"
TEST_END = "2024-12-31"

TRANSACTION_COST = 0.001
SLIPPAGE = 0.0005
INITIAL_CAPITAL = 100000

INCOMPATIBLE_STRATEGIES = {
    # Requires two assets, not one ticker OHLCV
    "pairs_trading",
}

LOCAL_REGIMES = ["Bull", "Bear", "Choppy"]


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        val = float(x)
    except Exception:
        return default
    return val if math.isfinite(val) else default


def _round(x: Any, digits: int = 3) -> float:
    return round(_safe_float(x), digits)


def _json_ready(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json_ready(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_ready(v) for v in obj]
    if isinstance(obj, tuple):
        return [_json_ready(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return obj


def print_header(title: str) -> None:
    print(f"\n{'=' * 78}")
    print(f"  {title}")
    print(f"{'=' * 78}")


def print_sub(title: str) -> None:
    print(f"\n  -- {title}")


@dataclass
class ScriptConfig:
    output_dir: Path
    output_file: Path
    checkpoint_file: Path
    max_tickers: Optional[int]
    dry_run: bool
    resume: bool
    sleep_between_secs: float
    resume_completed_tickers: List[str]


class DataFetcher:
    def __init__(self) -> None:
        self.cache: Dict[str, pd.DataFrame] = {}

    def fetch(self, ticker: str, start: str, end: str, market: str) -> Optional[pd.DataFrame]:
        key = f"{ticker}|{start}|{end}|{market}"
        if key in self.cache:
            return self.cache[key]

        try:
            df = get_history(
                ticker=ticker,
                start=start,
                end=end,
                market=market,
                interval="1d",
            )
            if df is None or df.empty or len(df) < 80:
                return None
            df = df.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            required = ["Open", "High", "Low", "Close", "Volume"]
            if not set(required).issubset(df.columns):
                return None
            df = df[required].dropna()
            if len(df) < 80:
                return None
            self.cache[key] = df
            return df
        except Exception:
            return None


def detect_daily_regimes(df: pd.DataFrame) -> pd.Series:
    close = df["Close"].astype(float)
    returns = close.pct_change().fillna(0.0)
    roll_vol = returns.rolling(20).std() * np.sqrt(252)
    roll_ret = returns.rolling(20).mean() * 252

    roll_vol = roll_vol.fillna(roll_vol.mean() if not roll_vol.empty else 0.0)
    roll_ret = roll_ret.fillna(0.0)

    vol_thresh = _safe_float(roll_vol.quantile(0.66), 0.0)
    labels: List[str] = []
    for i in range(len(df)):
        v = _safe_float(roll_vol.iloc[i], 0.0)
        r = _safe_float(roll_ret.iloc[i], 0.0)
        if v > vol_thresh:
            labels.append("Choppy")
        elif r > 0.05:
            labels.append("Bull")
        else:
            labels.append("Bear")
    return pd.Series(labels, index=df.index, name="Regime")


def _calc_metrics_from_backtest_df(
    backtest_df: pd.DataFrame,
    transaction_cost: float,
    slippage: float,
    initial_capital: float = INITIAL_CAPITAL,
) -> Optional[Dict[str, float]]:
    if backtest_df is None or backtest_df.empty:
        return None
    if "position" not in backtest_df.columns:
        return None
    if "pct_change" not in backtest_df.columns:
        return None

    df = backtest_df.copy()
    position = df["position"].fillna(0.0).astype(float)
    asset_ret = df["pct_change"].fillna(0.0).astype(float)

    trades = position.diff().abs().fillna(0.0)
    trade_cost = trades * (transaction_cost + slippage)
    strategy_ret = position * asset_ret - trade_cost

    equity = (1.0 + strategy_ret).cumprod() * float(initial_capital)
    if equity.empty:
        return None

    ann_vol = _safe_float(strategy_ret.std() * np.sqrt(252), 0.0)
    ann_return = _safe_float((equity.iloc[-1] / initial_capital) ** (252 / max(len(equity), 1)) - 1, 0.0)
    sharpe = ann_return / (ann_vol + 1e-9)

    peak = equity.cummax()
    dd = (equity - peak) / peak.replace(0, np.nan)
    max_dd = _safe_float(dd.min(), 0.0)

    active = strategy_ret[strategy_ret != 0]
    win_rate = _safe_float((active > 0).mean() * 100, 0.0) if len(active) else 0.0
    avg_win = _safe_float(active[active > 0].mean(), 0.0) if (active > 0).any() else 0.0
    avg_loss = _safe_float(active[active < 0].mean(), 0.0) if (active < 0).any() else 0.0
    win_loss = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0

    return {
        "annual_return": _round(ann_return * 100, 2),
        "annual_vol": _round(ann_vol * 100, 2),
        "sharpe": _round(sharpe, 3),
        "max_drawdown": _round(max_dd * 100, 2),
        "win_rate": _round(win_rate, 2),
        "win_loss_ratio": _round(win_loss, 2),
        "n_trades": int((trades > 0).sum()),
        "final_equity": _round(equity.iloc[-1], 2),
        "net_returns_series": strategy_ret,
        "position_series": position,
    }


def _calc_benchmark_metrics(df: Optional[pd.DataFrame]) -> Optional[Dict[str, float]]:
    if df is None or df.empty or "Close" not in df.columns:
        return None
    close = df["Close"].astype(float)
    ret = close.pct_change().fillna(0.0)
    equity = (1.0 + ret).cumprod()
    if equity.empty:
        return None
    ann_return = _safe_float((equity.iloc[-1]) ** (252 / max(len(equity), 1)) - 1, 0.0)
    ann_vol = _safe_float(ret.std() * np.sqrt(252), 0.0)
    sharpe = ann_return / (ann_vol + 1e-9)
    peak = equity.cummax()
    dd = (equity - peak) / peak.replace(0, np.nan)
    max_dd = _safe_float(dd.min(), 0.0)
    return {
        "annual_return": _round(ann_return * 100, 2),
        "sharpe": _round(sharpe, 3),
        "max_drawdown": _round(max_dd * 100, 2),
    }


def _confidence_from_backend_formula(
    sharpe: float,
    win_rate: float,
    annual_vol: float,
    regime_now: str,
    last_signal: float,
) -> float:
    financial = np.clip((sharpe + 1.0) * 40.0, 0.0, 100.0)
    sentiment = 50.0
    regime_l = regime_now.lower()
    if "bull" in regime_l and last_signal > 0:
        sentiment = 75.0
    elif "bear" in regime_l and last_signal < 0:
        sentiment = 75.0
    elif "volatility" in regime_l:
        sentiment = 40.0
    sector = np.clip(win_rate, 0.0, 100.0)
    emotion_penalty = np.clip(annual_vol / 3.0, 0.0, 30.0)
    return calculate_confidence(
        financial_score=float(financial),
        sentiment_score=float(sentiment),
        sector_score=float(sector),
        emotion_penalty=float(emotion_penalty),
    )


def _measure_ms(fn, *args, **kwargs) -> Tuple[Any, float]:
    t0 = time.perf_counter()
    out = fn(*args, **kwargs)
    return out, round((time.perf_counter() - t0) * 1000.0, 2)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(_json_ready(data), f, indent=2)


def _strategy_universe() -> List[str]:
    strategies = sorted(STRATEGY_REGISTRY.keys())
    return [s for s in strategies if s not in INCOMPATIBLE_STRATEGIES]


def _friendly_strategy_name(strategy_key: str) -> str:
    return strategy_key.replace("_", " ").title()


def _load_resume_checkpoint(checkpoint_file: Path) -> List[str]:
    if not checkpoint_file.exists():
        return []
    try:
        with checkpoint_file.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        completed = payload.get("completed_tickers") or []
        return [str(x) for x in completed]
    except Exception:
        return []


def run_kpi_suite(cfg: ScriptConfig) -> Dict[str, Any]:
    fetcher = DataFetcher()
    backend_regime_detector = BackendRegimeDetector()

    strategies = _strategy_universe()
    rl = BackendRLStrategySelector(
        strategies=strategies,
        q_table_path=str(cfg.output_dir / "trained_qtable.json"),
    )

    results: Dict[str, Dict[str, Any]] = defaultdict(dict)
    regime_perf: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    bench_results: Dict[str, Any] = {}
    errors: List[Dict[str, str]] = []

    all_sharpes: List[float] = []
    all_returns: List[float] = []
    total_trades = 0
    tickers_tested = 0
    completed_tickers: List[str] = list(cfg.resume_completed_tickers)
    market_return_tracker: Dict[str, List[float]] = defaultdict(list)

    markets = {
        "NIFTY50": {
            "tickers": NIFTY_50_TICKERS,
            "market_code": "INDIA",
        },
        "SP500": {
            "tickers": SP500_TICKERS,
            "market_code": "US",
        },
    }

    if cfg.max_tickers is not None and cfg.max_tickers > 0:
        for market_name in markets:
            markets[market_name]["tickers"] = markets[market_name]["tickers"][: cfg.max_tickers]

    print_header("BENCHMARK PERFORMANCE")
    for market_name, bench_ticker in BENCHMARKS.items():
        df_bench = fetcher.fetch(
            ticker=bench_ticker,
            start=TEST_START,
            end=TEST_END,
            market="US",
        )
        metrics = _calc_benchmark_metrics(df_bench)
        if metrics:
            bench_results[market_name] = metrics
            print(
                f"  {market_name:10} | Return: {metrics['annual_return']:>7.2f}%  "
                f"Sharpe: {metrics['sharpe']:>6.3f}  MaxDD: {metrics['max_drawdown']:>7.2f}%"
            )
        else:
            print(f"  {market_name:10} | Benchmark unavailable")

    for market_name, market_cfg in markets.items():
        tickers = market_cfg["tickers"]
        market_code = market_cfg["market_code"]

        print_header(f"MARKET: {market_name}  ({len(tickers)} stocks)")
        market_sharpes: List[float] = []
        market_returns: List[float] = []
        strategy_sharpes: Dict[str, List[float]] = defaultdict(list)

        for ticker in tickers:
            if ticker in completed_tickers:
                print(f"    {ticker:20} | skipped (already completed in checkpoint)")
                continue

            (df_train, fetch_train_ms) = _measure_ms(fetcher.fetch, ticker, TRAIN_START, TRAIN_END, market_code)
            (df_test, fetch_test_ms) = _measure_ms(fetcher.fetch, ticker, TEST_START, TEST_END, market_code)

            if df_train is None or df_test is None:
                msg = f"Skipped {ticker}: missing train/test data"
                print(f"    {ticker:20} | {msg}")
                errors.append({"ticker": ticker, "error": msg})
                if cfg.sleep_between_secs > 0 and not cfg.dry_run:
                    time.sleep(cfg.sleep_between_secs)
                continue

            tickers_tested += 1
            completed_tickers.append(ticker)

            (daily_regimes, local_regime_ms) = _measure_ms(detect_daily_regimes, df_test)

            (backend_regime_now, backend_regime_ms) = _measure_ms(backend_regime_detector.detect, ticker)
            if not isinstance(backend_regime_now, dict):
                backend_regime_now = {"regime": "Unknown", "volatility": 0.0}

            ticker_best = {"strategy": "N/A", "sharpe": -999.0}

            for strategy_name in strategies:
                try:
                    bt_train_df = run_backtest_on_df(df_train.copy(), strategy_name, initial_capital=INITIAL_CAPITAL)
                    bt_test_df = run_backtest_on_df(df_test.copy(), strategy_name, initial_capital=INITIAL_CAPITAL)
                except Exception as exc:
                    errors.append(
                        {
                            "ticker": ticker,
                            "strategy": strategy_name,
                            "error": f"Backtest failed: {exc}",
                        }
                    )
                    continue

                train_metrics = _calc_metrics_from_backtest_df(
                    bt_train_df,
                    transaction_cost=TRANSACTION_COST,
                    slippage=SLIPPAGE,
                    initial_capital=INITIAL_CAPITAL,
                )
                test_metrics = _calc_metrics_from_backtest_df(
                    bt_test_df,
                    transaction_cost=TRANSACTION_COST,
                    slippage=SLIPPAGE,
                    initial_capital=INITIAL_CAPITAL,
                )
                if not test_metrics:
                    continue

                if train_metrics:
                    reward = _safe_float(train_metrics["annual_return"] / 100.0)
                    regime_now = backend_regime_now.get("regime", "Unknown")
                    rl.update(regime_now, strategy_name, reward)

                sharpe = _safe_float(test_metrics["sharpe"])
                ann_return = _safe_float(test_metrics["annual_return"])
                ann_vol = _safe_float(test_metrics["annual_vol"])
                n_trades = int(test_metrics["n_trades"])

                total_trades += n_trades
                market_sharpes.append(sharpe)
                market_returns.append(ann_return)
                market_return_tracker[market_name].append(ann_return)
                strategy_sharpes[strategy_name].append(sharpe)
                all_sharpes.append(sharpe)
                all_returns.append(ann_return)

                if sharpe > ticker_best["sharpe"]:
                    ticker_best = {"strategy": strategy_name, "sharpe": sharpe}

                net_returns = test_metrics.get("net_returns_series")
                if isinstance(net_returns, pd.Series):
                    for regime in LOCAL_REGIMES:
                        mask = daily_regimes == regime
                        if mask.sum() < 20:
                            continue
                        regime_ret = net_returns[mask].dropna()
                        if len(regime_ret) < 20:
                            continue
                        regime_ann_ret = _safe_float((1.0 + regime_ret).prod() ** (252 / len(regime_ret)) - 1, 0.0)
                        regime_ann_vol = _safe_float(regime_ret.std() * np.sqrt(252), 0.0)
                        regime_sharpe = regime_ann_ret / (regime_ann_vol + 1e-9)
                        regime_perf[regime][strategy_name].append(_round(regime_sharpe, 3))

                position_series = test_metrics.get("position_series")
                last_signal = 0.0
                if isinstance(position_series, pd.Series) and not position_series.empty:
                    last_signal = _safe_float(position_series.iloc[-1])

                conf = _confidence_from_backend_formula(
                    sharpe=sharpe,
                    win_rate=_safe_float(test_metrics["win_rate"]),
                    annual_vol=ann_vol,
                    regime_now=str(backend_regime_now.get("regime", "Unknown")),
                    last_signal=last_signal,
                )

                results[market_name][f"{ticker}_{strategy_name}"] = {
                    "strategy": strategy_name,
                    "strategy_display": _friendly_strategy_name(strategy_name),
                    "sharpe": sharpe,
                    "annual_return": ann_return,
                    "max_drawdown": _safe_float(test_metrics["max_drawdown"]),
                    "win_rate": _safe_float(test_metrics["win_rate"]),
                    "n_trades": n_trades,
                    "confidence": conf,
                    "backend_regime_now": backend_regime_now.get("regime", "Unknown"),
                    "daily_regime_last": str(daily_regimes.iloc[-1]),
                }

            print(
                f"    {ticker:20} | Best: {_friendly_strategy_name(ticker_best['strategy']):24} "
                f"Sharpe: {ticker_best['sharpe']:>6.3f} "
                f"[train_fetch:{fetch_train_ms}ms test_fetch:{fetch_test_ms}ms "
                f"local_regime:{local_regime_ms}ms backend_regime:{backend_regime_ms}ms]"
            )

            checkpoint = {
                "timestamp": datetime.now().isoformat(),
                "stage": "running",
                "completed_tickers": completed_tickers,
                "tickers_tested": tickers_tested,
                "total_trades": total_trades,
                "errors_so_far": errors[-20:],
            }
            _write_json(cfg.checkpoint_file, checkpoint)

            if cfg.dry_run:
                break

            if cfg.sleep_between_secs > 0:
                time.sleep(cfg.sleep_between_secs)

        if market_sharpes:
            avg_sharpe = _round(np.mean(market_sharpes), 3)
            med_sharpe = _round(np.median(market_sharpes), 3)
            avg_return = _round(np.mean(market_returns), 2)
            best_strategy = max(
                strategy_sharpes,
                key=lambda s: np.mean(strategy_sharpes[s]) if strategy_sharpes[s] else -999.0,
            )
            best_strategy_sharpe = _round(np.mean(strategy_sharpes[best_strategy]), 3)
            bmk = bench_results.get(market_name, {})
            print_sub(f"{market_name} SUMMARY vs {market_name} BENCHMARK")
            print(
                f"    Avg Sharpe (all strats):  {avg_sharpe:>7.3f}   "
                f"(benchmark: {bmk.get('sharpe', 'N/A')})"
            )
            print(f"    Median Sharpe:            {med_sharpe:>7.3f}")
            print(
                f"    Avg Annual Return:        {avg_return:>7.2f}%  "
                f"(benchmark: {bmk.get('annual_return', 'N/A')}%)"
            )
            print(
                f"    Best Strategy:            {_friendly_strategy_name(best_strategy)} "
                f"(Sharpe {best_strategy_sharpe})"
            )
        else:
            print_sub(f"{market_name} SUMMARY")
            print("    No successful strategy runs for this market.")

        if cfg.dry_run:
            break

    print_header("RL STRATEGY SELECTOR — CURRENT BACKEND Q-TABLE")
    q_table = rl.get_q_table()
    ranked_q = sorted(q_table.items(), key=lambda kv: kv[1], reverse=True)
    for strategy_name, q_val in ranked_q[:8]:
        print(f"  {_friendly_strategy_name(strategy_name):30} Q={_round(q_val, 6):>10}")

    print_header("REGIME-STRATIFIED STRATEGY PERFORMANCE")
    for regime in LOCAL_REGIMES:
        print(f"\n  {regime} Market:")
        items = sorted(
            regime_perf[regime].items(),
            key=lambda kv: np.mean(kv[1]) if kv[1] else -999.0,
            reverse=True,
        )
        if not items:
            print("    No valid samples")
            continue
        for strategy_name, vals in items[:5]:
            print(
                f"    {_friendly_strategy_name(strategy_name):30} "
                f"avg Sharpe: {_round(np.mean(vals), 3):>7.3f}  n={len(vals)}"
            )

    regime_best_map: Dict[str, str] = {}
    for regime in LOCAL_REGIMES:
        items = sorted(
            regime_perf[regime].items(),
            key=lambda kv: np.mean(kv[1]) if kv[1] else -999.0,
            reverse=True,
        )
        regime_best_map[regime] = items[0][0] if items else "N/A"

    print_header("CONFIDENCE ENGINE — SAMPLE OUTPUTS")
    sample_rows = [
        {"financial": 78, "sentiment": 68, "sector": 60, "emotion_penalty": 8},
        {"financial": 65, "sentiment": 55, "sector": 52, "emotion_penalty": 15},
        {"financial": 44, "sentiment": 42, "sector": 48, "emotion_penalty": 22},
    ]
    print("  Financial  Sentiment  Sector  EmoPenalty -> Confidence")
    for row in sample_rows:
        conf = calculate_confidence(
            financial_score=row["financial"],
            sentiment_score=row["sentiment"],
            sector_score=row["sector"],
            emotion_penalty=row["emotion_penalty"],
        )
        print(
            f"  {row['financial']:>9}  {row['sentiment']:>9}  "
            f"{row['sector']:>6}  {row['emotion_penalty']:>10} -> {conf:>10}"
        )

    print_header("LATENCY BENCHMARKS")
    sample_ticker = SP500_TICKERS[0]
    sample_market = "US"

    _, cold_ms = _measure_ms(fetcher.fetch, sample_ticker, TEST_START, TEST_END, sample_market)
    _, hot_ms = _measure_ms(fetcher.fetch, sample_ticker, TEST_START, TEST_END, sample_market)
    sample_df = fetcher.fetch(sample_ticker, TEST_START, TEST_END, sample_market)

    if sample_df is not None:
        _, local_regime_ms = _measure_ms(detect_daily_regimes, sample_df)
        _, backend_regime_ms = _measure_ms(backend_regime_detector.detect, sample_ticker)
        strategy_obj = get_strategy("ema_crossover")
        _, signal_ms = _measure_ms(strategy_obj.generate_signals, sample_df.copy())
        _, bt_ms = _measure_ms(run_backtest_on_df, sample_df.copy(), "ema_crossover")
    else:
        local_regime_ms = -1.0
        backend_regime_ms = -1.0
        signal_ms = -1.0
        bt_ms = -1.0

    print(f"  Data fetch (cold):        {cold_ms:>8.2f} ms")
    print(
        f"  Data fetch (cached):      {hot_ms:>8.2f} ms   "
        f"({round(cold_ms / max(hot_ms, 0.01), 2)}x speedup)"
    )
    print(f"  Local regime detection:   {local_regime_ms:>8.2f} ms")
    print(f"  Backend regime snapshot:  {backend_regime_ms:>8.2f} ms")
    print(f"  Signal generation:        {signal_ms:>8.2f} ms")
    print(f"  Full backtest (1 ticker): {bt_ms:>8.2f} ms")

    print_header("FINAL KPI SUMMARY — PROJECT-ALIGNED")

    overall_sharpe = _round(np.mean(all_sharpes), 3) if all_sharpes else 0.0
    overall_return = _round(np.mean(all_returns), 2) if all_returns else 0.0
    pos_sharpe_pct = _round((np.array(all_sharpes) > 0).mean() * 100, 1) if all_sharpes else 0.0

    strategy_global: Dict[str, List[float]] = defaultdict(list)
    for regime in LOCAL_REGIMES:
        for strategy_name, vals in regime_perf[regime].items():
            strategy_global[strategy_name].extend(vals)

    if strategy_global:
        best_strategy_name = max(
            strategy_global,
            key=lambda s: np.mean(strategy_global[s]) if strategy_global[s] else -999.0,
        )
        best_strategy_sharpe = (
            _round(np.mean(strategy_global[best_strategy_name]), 3)
            if strategy_global[best_strategy_name]
            else "N/A"
        )
    else:
        best_strategy_name = "N/A"
        best_strategy_sharpe = "N/A"

    alpha_vs_nifty = "N/A"
    alpha_vs_sp500 = "N/A"
    if market_return_tracker["NIFTY50"] and "NIFTY50" in bench_results:
        alpha_vs_nifty = _round(
            np.mean(market_return_tracker["NIFTY50"]) - bench_results["NIFTY50"]["annual_return"],
            2,
        )
    if market_return_tracker["SP500"] and "SP500" in bench_results:
        alpha_vs_sp500 = _round(
            np.mean(market_return_tracker["SP500"]) - bench_results["SP500"]["annual_return"],
            2,
        )

    print(
        f"""
  +------------------------------------------------------------------+
  |  METRIC                              VALUE                       |
  +------------------------------------------------------------------+
  |  Avg Sharpe Ratio (OOS)              {overall_sharpe:<26} |
  |  Avg Annual Return (OOS)             {str(overall_return) + '%':<26} |
  |  Strategies tested                   {len(strategies):<26} |
  |  Tickers covered                     {tickers_tested:<26} |
  |  Total trades simulated              {total_trades:<26,} |
  |  Strategies with +ve Sharpe          {str(pos_sharpe_pct) + '%':<26} |
  |  Best Strategy (regime-adjusted)     {_friendly_strategy_name(best_strategy_name):<26} |
  |  Best Strategy Sharpe                {best_strategy_sharpe:<26} |
  |  Alpha vs Nifty 50                   {str(alpha_vs_nifty) + '%':<26} |
  |  Alpha vs S&P 500                    {str(alpha_vs_sp500) + '%':<26} |
  |  Trading friction modeled            0.15% per turnover unit     |
  +------------------------------------------------------------------+
"""
    )

    output: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "train_period": [TRAIN_START, TRAIN_END],
            "test_period": [TEST_START, TEST_END],
            "transaction_cost": TRANSACTION_COST,
            "slippage": SLIPPAGE,
            "initial_capital": INITIAL_CAPITAL,
            "strategies_used": strategies,
            "strategies_skipped": sorted(INCOMPATIBLE_STRATEGIES),
            "architecture_alignment": {
                "strategy_source": "backend.services.strategies.strategy_adapter.STRATEGY_REGISTRY",
                "backtest_engine": "backend.services.backtest_service.run_backtest_on_df",
                "confidence_engine": "backend.engine.confidence_engine.calculate_confidence",
                "rl_selector": "backend.quant.rl_strategy_selector.RLStrategySelector",
                "regime_note": (
                    "Per-day regime segmentation uses local rolling labels (Bull/Bear/Choppy) "
                    "because backend.regime_detector currently returns a single latest regime snapshot."
                ),
            },
        },
        "kpis": {
            "avg_sharpe_oos": overall_sharpe,
            "avg_annual_return_pct": overall_return,
            "tickers_tested": tickers_tested,
            "total_trades": total_trades,
            "positive_sharpe_pct": pos_sharpe_pct,
            "best_strategy": best_strategy_name,
            "best_strategy_sharpe": best_strategy_sharpe,
            "best_strategy_regime_adjusted": best_strategy_name,
            "best_strategy_regime_sharpe": best_strategy_sharpe,
            "alpha_vs_nifty50_pct": alpha_vs_nifty,
            "alpha_vs_sp500_pct": alpha_vs_sp500,
        },
        "benchmarks": bench_results,
        "q_table": q_table,
        "regime_best_strategy_from_oos": regime_best_map,
        "latency_ms": {
            "cold_fetch": cold_ms,
            "cached_fetch": hot_ms,
            "local_regime_detection": local_regime_ms,
            "backend_regime_detection": backend_regime_ms,
            "signal_generation": signal_ms,
            "full_backtest": bt_ms,
        },
        "results": results,
        "errors": errors,
    }

    # Prepare separate outputs
    summary_output = {
        "timestamp": output["timestamp"],
        "config": output["config"],
        "kpis": output["kpis"],
        "benchmarks": output["benchmarks"],
        "regime_best_strategy_from_oos": output["regime_best_strategy_from_oos"],
        "latency_ms": output["latency_ms"],
        "error_summary": {
            "total_errors": len(errors),
            "tickers_with_errors": list(set(e.get("ticker", "unknown") for e in errors)),
        }
    }

    # 1. Save main summary (no huge 'results' or 'q_table' dump)
    _write_json(cfg.output_dir / "bloomberg_summary.json", summary_output)

    # 2. Save Q-table separately if it was updated/generated
    _write_json(cfg.output_dir / "kpi_q_table_final.json", q_table)

    # 3. Save detailed results per market
    for market_name, market_results in results.items():
        fname = f"results_{market_name.lower().replace(' ', '_')}.json"
        _write_json(cfg.output_dir / fname, market_results)

    # 4. Keep the original combined file for compatibility, but print separation info
    _write_json(cfg.output_file, output)

    print(f"  [Output] Main Summary:    {cfg.output_dir / 'bloomberg_summary.json'}")
    for market_name in results.keys():
        fname = f"results_{market_name.lower().replace(' ', '_')}.json"
        print(f"  [Output] Market Results:  {cfg.output_dir / fname}")
    print(f"  [Output] Combined Log:    {cfg.output_file}")
    print(f"  Checkpoint file:  {cfg.checkpoint_file}")
    print(f"  Completed at:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return output


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run architecture-aligned KPI suite.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path("outputs")),
        help="Directory for KPI json and checkpoint files.",
    )
    parser.add_argument(
        "--max-tickers",
        type=int,
        default=None,
        help="Optional cap per market for faster runs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process only first valid ticker in first market for smoke testing.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from outputs/bloomberg_kpi_checkpoint.json by skipping completed tickers.",
    )
    parser.add_argument(
        "--sleep-between",
        type=float,
        default=0.5,
        help="Sleep seconds between tickers to reduce yfinance rate limiting.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    out_dir = Path(args.output_dir)
    checkpoint_file = out_dir / "bloomberg_kpi_checkpoint.json"
    resume_completed = _load_resume_checkpoint(checkpoint_file) if args.resume else []

    cfg = ScriptConfig(
        output_dir=out_dir,
        output_file=out_dir / "bloomberg_kpis.json",
        checkpoint_file=checkpoint_file,
        max_tickers=args.max_tickers,
        dry_run=bool(args.dry_run),
        resume=bool(args.resume),
        sleep_between_secs=max(0.0, float(args.sleep_between)),
        resume_completed_tickers=resume_completed,
    )

    print("\n  Bloomberg Quant KPI Test Suite (Architecture-Aligned)")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Train:   {TRAIN_START} -> {TRAIN_END}")
    print(f"  Test:    {TEST_START} -> {TEST_END} (out-of-sample)")
    print(f"  Output:  {cfg.output_file}")
    print(f"  Mode:    {'DRY-RUN' if cfg.dry_run else 'FULL'}")
    print(f"  Resume:  {'ON' if cfg.resume else 'OFF'}")
    print(f"  Sleep:   {cfg.sleep_between_secs}s between tickers")
    if cfg.resume:
        print(f"  Loaded completed tickers from checkpoint: {len(cfg.resume_completed_tickers)}")

    try:
        run_kpi_suite(cfg)
    except KeyboardInterrupt:
        print("\nRun interrupted by user. Partial progress is in checkpoint JSON.")
    except Exception as exc:
        print("\nKPI suite failed with an unexpected error.")
        print(f"Error: {exc}")
        print(traceback.format_exc())
        _write_json(
            cfg.checkpoint_file,
            {
                "timestamp": datetime.now().isoformat(),
                "stage": "failed",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        raise


if __name__ == "__main__":
    main()
