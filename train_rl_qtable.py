"""
Bloomberg Quant — RL Q-Table Training Script
=============================================
Trains the regime-aware Q-table on 5 years of historical data
(2018-2022) so the RL agent has genuine learned experience before
any live or paper trading begins.

What this script does step by step:
1. Fetches 5 years of daily OHLCV for Nifty 50 + S&P 500 tickers
2. For each ticker, detects regime (Bull/Bear/Choppy) on every window
3. Slides a 60-day window through the training data
4. At each window, calculates forward return for every strategy
5. Calls rl.update(regime, strategy, reward) for each
6. After all tickers, saves trained Q-table to JSON
7. Prints validation report showing what the agent learned

A properly trained Q-table looks like this:
    "Bull_fibonacci_pullback":   2.4   <- learned: good in bull
    "Bull_macd":                -0.8   <- learned: bad in bull
    "Bear_mean_reversion":       0.9   <- learned: good in bear
    "Choppy_rsi_reversal":       1.1   <- learned: good in choppy

Run:
    cd C:\\Users\\PaarthGala\\Bloomberg
    .\\backend\\.venv\\Scripts\\python.exe train_rl_qtable.py
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import time
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def _check_deps():
    missing = [m for m in ["numpy", "pandas", "yfinance"]
               if importlib.util.find_spec(m) is None]
    if missing:
        print(f"Missing: {', '.join(missing)}")
        print("Run: pip install numpy pandas yfinance")
        raise SystemExit(1)


_check_deps()

import numpy as np
import pandas as pd

try:
    from backend.services.backtest_service import run_backtest_on_df
    from backend.services.data_loader import get_history
    from backend.services.strategies.strategy_adapter import STRATEGY_REGISTRY
except Exception as exc:
    print(f"Backend import failed: {exc}")
    print("Run from project root: cd C:\\Users\\PaarthGala\\Bloomberg")
    raise SystemExit(1)

print("Backend modules loaded.\n")


# -----------------------------------------------------------------------------
# CONFIG — tune these if the run is too slow or too fast
# -----------------------------------------------------------------------------

TRAIN_START = "2018-01-01"
TRAIN_END   = "2022-12-31"

WINDOW_SIZE  = 60   # days of history used to detect regime
FORWARD_DAYS = 21   # days ahead to measure strategy reward
STEP_SIZE    = 10   # slide window every N days
                    # 1 = maximum updates but slow (~3 hrs)
                    # 5 = good balance (~35 mins)
                    # 10 = fast smoke test (~18 mins)

TRANSACTION_COST = 0.001
SLIPPAGE         = 0.0005

OUTPUT_DIR  = Path("outputs")
OUTPUT_FILE = OUTPUT_DIR / "trained_qtable.json"

NIFTY_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "WIPRO.NS",
    "ULTRACEMCO.NS", "TITAN.NS", "BAJFINANCE.NS", "NESTLEIND.NS", "POWERGRID.NS",
]

SP500_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "BRK-B", "UNH", "JPM",
    "V", "JNJ", "XOM", "PG", "MA",
    "HD", "CVX", "MRK", "ABBV", "PEP",
]

SKIP_STRATEGIES = {"pairs_trading"}


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def safe(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def fetch_ticker(ticker: str, start: str, end: str,
                 market: str, cache: Dict) -> Optional[pd.DataFrame]:
    key = f"{ticker}|{start}|{end}"
    if key in cache:
        return cache[key]
    try:
        df = get_history(ticker=ticker, start=start, end=end,
                         market=market, interval="1d")
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        needed = ["Open", "High", "Low", "Close", "Volume"]
        if not set(needed).issubset(df.columns):
            return None
        df = df[needed].dropna()
        min_rows = WINDOW_SIZE + FORWARD_DAYS + 10
        if len(df) < min_rows:
            return None
        cache[key] = df
        return df
    except Exception:
        return None


def detect_regime(window_df: pd.DataFrame) -> str:
    """
    Classify regime at the end of a 60-day window.
    Uses rolling volatility and trend — same logic as your HMM proxy.

    Returns: "Bull", "Bear", or "Choppy"
    """
    close   = window_df["Close"].astype(float)
    returns = close.pct_change().dropna()
    if len(returns) < 10:
        return "Choppy"

    ann_vol = safe(returns.std() * np.sqrt(252))
    ann_ret = safe(returns.mean() * 252)

    # >30% annualised vol = high volatility / choppy
    if ann_vol > 0.30:
        return "Choppy"
    elif ann_ret > 0.05:
        return "Bull"
    else:
        return "Bear"


def calc_forward_return(df: pd.DataFrame, start_idx: int,
                        strategy_name: str) -> float:
    """
    Run backtest on next FORWARD_DAYS and return net return as reward.
    Positive = strategy made money. Negative = strategy lost money.
    """
    end_idx = min(start_idx + FORWARD_DAYS, len(df))
    if end_idx <= start_idx or end_idx - start_idx < 2:
        return 0.0

    fwd = df.iloc[start_idx:end_idx].copy()
    try:
        bt = run_backtest_on_df(fwd, strategy_name, initial_capital=10000)
        if bt is None or bt.empty:
            return 0.0
        if "pct_change" not in bt.columns or "position" not in bt.columns:
            return 0.0

        pos    = bt["position"].fillna(0.0).astype(float)
        ret    = bt["pct_change"].fillna(0.0).astype(float)
        trades = pos.diff().abs().fillna(0.0)
        net    = pos * ret - trades * (TRANSACTION_COST + SLIPPAGE)

        total = safe((1.0 + net).prod() - 1.0)
        return total * (252 / FORWARD_DAYS)
    except Exception:
        return 0.0


# -----------------------------------------------------------------------------
# REGIME-AWARE RL
# -----------------------------------------------------------------------------

class RegimeAwareRL:
    """
    Q-learning with regime as part of the state.
    Keys are "Bull_fibonacci_pullback", "Bear_mean_reversion", etc.

    This is the fix for your current backend which stores flat keys
    like "fibonacci_pullback" with no regime separation.
    """

    def __init__(self, strategies: List[str],
                 lr: float = 0.1,
                 gamma: float = 0.95,
                 epsilon: float = 1.0,
                 epsilon_min: float = 0.05,
                 epsilon_decay: float = 0.9995):
        self.strategies    = strategies
        self.lr            = lr
        self.gamma         = gamma
        self.epsilon       = epsilon
        self.epsilon_min   = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q: Dict[str, float] = {}
        self.update_count  = 0
        self.reward_log: Dict[str, List[float]] = defaultdict(list)

    def _key(self, regime: str, strategy: str) -> str:
        return f"{regime}_{strategy}"

    def update(self, regime: str, strategy: str, reward: float) -> None:
        """
        Q-learning Bellman update.

        new_Q = old_Q + lr * (reward + gamma * max_future_Q - old_Q)

        Step by step:
        - old_Q         = current belief about this strategy in this regime
        - reward        = what actually happened (forward return)
        - max_future_Q  = best Q available for same regime next step
        - gap           = reward + gamma*max_future - old_Q
                          positive gap → Q goes up (better than expected)
                          negative gap → Q goes down (worse than expected)
        - lr * gap      = how much to move (0.1 = 10% nudge per update)
        """
        k = self._key(regime, strategy)
        old_q = self.q.get(k, 0.0)

        future_qs  = [self.q.get(self._key(regime, s), 0.0)
                      for s in self.strategies]
        max_future = max(future_qs) if future_qs else 0.0

        new_q = old_q + self.lr * (reward + self.gamma * max_future - old_q)
        self.q[k] = round(new_q, 6)

        self.reward_log[k].append(reward)
        self.update_count += 1

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def full_table(self) -> Dict[str, Dict[str, float]]:
        result = {}
        for regime in ["Bull", "Bear", "Choppy"]:
            result[regime] = {
                s: round(self.q.get(self._key(regime, s), 0.0), 4)
                for s in self.strategies
            }
        return result

    def best_per_regime(self) -> Dict[str, Tuple[str, float]]:
        out = {}
        for regime in ["Bull", "Bear", "Choppy"]:
            scores = {s: self.q.get(self._key(regime, s), 0.0)
                      for s in self.strategies}
            if not scores:
                out[regime] = ("None", 0.0)
                continue
            best = max(scores, key=scores.get)
            out[regime] = (best, round(scores[best], 4))
        return out

    def worst_per_regime(self) -> Dict[str, Tuple[str, float]]:
        out = {}
        for regime in ["Bull", "Bear", "Choppy"]:
            scores = {s: self.q.get(self._key(regime, s), 0.0)
                      for s in self.strategies}
            if not scores:
                out[regime] = ("None", 0.0)
                continue
            worst = min(scores, key=scores.get)
            out[regime] = (worst, round(scores[worst], 4))
        return out

    def spread(self) -> Dict[str, float]:
        """
        Max Q - Min Q per regime.
        Wide spread = agent has learned strong differentiation.
        Tight spread (< 0.05) = barely trained, essentially random.
        """
        out = {}
        for regime in ["Bull", "Bear", "Choppy"]:
            vals = [self.q.get(self._key(regime, s), 0.0)
                    for s in self.strategies]
            if not vals:
                out[regime] = 0.0
                continue
            out[regime] = round(max(vals) - min(vals), 4)
        return out

    def save(self, path: Path) -> None:
        payload = {
            "timestamp":         datetime.now().isoformat(),
            "update_count":      self.update_count,
            "final_epsilon":     round(self.epsilon, 6),
            "q_table_flat":      self.q,
            "q_table_by_regime": self.full_table(),
            "best_per_regime": {
                r: {"strategy": s, "q_value": v}
                for r, (s, v) in self.best_per_regime().items()
            },
            "worst_per_regime": {
                r: {"strategy": s, "q_value": v}
                for r, (s, v) in self.worst_per_regime().items()
            },
            "spread_per_regime": self.spread(),
            "update_counts_per_key": {
                k: len(v) for k, v in self.reward_log.items()
            },
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\n  Saved -> {path}")


# -----------------------------------------------------------------------------
# TRAINING LOOP
# -----------------------------------------------------------------------------

def train():
    strategies = sorted(
        [s for s in STRATEGY_REGISTRY.keys() if s not in SKIP_STRATEGIES]
    )
    rl    = RegimeAwareRL(strategies)
    cache: Dict[str, pd.DataFrame] = {}

    markets = [
        ("NIFTY", NIFTY_TICKERS, "INDIA"),
        ("SP500", SP500_TICKERS, "US"),
    ]

    total_windows  = 0
    total_updates  = 0
    skipped        = 0
    t_start        = time.time()

    print("=" * 65)
    print("  TRAINING PHASE")
    print(f"  Period:     {TRAIN_START} -> {TRAIN_END}")
    print(f"  Strategies: {len(strategies)}")
    print(f"  Window:     {WINDOW_SIZE}d  Forward: {FORWARD_DAYS}d  Step: {STEP_SIZE}d")
    print("=" * 65)

    for market_name, tickers, market_code in markets:
        print(f"\n  [{market_name}] - {len(tickers)} tickers")

        for idx, ticker in enumerate(tickers):
            df = fetch_ticker(ticker, TRAIN_START, TRAIN_END,
                              market_code, cache)

            if df is None:
                print(f"    {idx+1:02}/{len(tickers)}  {ticker:20} - skipped (no data)")
                skipped += 1
                time.sleep(0.5)
                continue

            windows_this_ticker = 0

            for w in range(0, len(df) - WINDOW_SIZE - FORWARD_DAYS, STEP_SIZE):
                window_df = df.iloc[w: w + WINDOW_SIZE]
                regime    = detect_regime(window_df)

                for strategy in strategies:
                    reward = calc_forward_return(df, w + WINDOW_SIZE, strategy)
                    rl.update(regime, strategy, reward)
                    total_updates += 1

                windows_this_ticker += 1
                total_windows += 1

            elapsed = round(time.time() - t_start, 1)
            print(
                f"    {idx+1:02}/{len(tickers)}  {ticker:20} "
                f"windows:{windows_this_ticker:>4}  "
                f"total_updates:{total_updates:>7,}  "
                f"epsilon:{round(rl.epsilon,3):<6}  "
                f"elapsed:{elapsed}s"
            )

            time.sleep(0.5)

    # -------------------------------------------------------------------------
    # VALIDATION REPORT
    # -------------------------------------------------------------------------

    elapsed_total = round(time.time() - t_start, 1)

    print("\n" + "=" * 65)
    print("  TRAINING COMPLETE")
    print("=" * 65)
    print(f"  Total windows:       {total_windows:,}")
    print(f"  Total Q updates:     {total_updates:,}")
    print(f"  Skipped tickers:     {skipped}")
    print(f"  Final epsilon:       {round(rl.epsilon, 4)}")
    print(f"  Time taken:          {elapsed_total}s")

    print("\n  Q-VALUE SPREAD PER REGIME")
    print("  (>0.5 = strong learning  |  <0.05 = untrained)")
    spreads = rl.spread()
    for regime, sp in spreads.items():
        bar     = "#" * int(sp * 15)
        quality = "STRONG" if sp > 0.5 else "MODERATE" if sp > 0.1 else "WEAK - needs more data"
        print(f"    {regime:8}  spread={sp:.4f}  {bar:<20}  {quality}")

    print("\n  BEST STRATEGY PER REGIME")
    for regime, (strategy, q_val) in rl.best_per_regime().items():
        print(f"    {regime:8} -> {strategy:30}  Q={q_val}")

    print("\n  WORST STRATEGY PER REGIME")
    for regime, (strategy, q_val) in rl.worst_per_regime().items():
        print(f"    {regime:8} -> {strategy:30}  Q={q_val}")

    print("\n  FULL Q-TABLE BY REGIME")
    full = rl.full_table()
    for regime in ["Bull", "Bear", "Choppy"]:
        print(f"\n    {regime}:")
        ranked = sorted(full[regime].items(), key=lambda x: x[1], reverse=True)
        for strategy, q_val in ranked:
            bar = "#" * max(0, int((q_val + 0.2) * 10))
            print(f"      {strategy:30}  {q_val:>8.4f}  {bar}")

    print("\n  SANITY CHECK")
    trend_strats     = {"fibonacci_pullback", "support_resistance",
                        "momentum", "ema_crossover", "breakout"}
    reversion_strats = {"mean_reversion", "rsi_reversal",
                        "rsi_momentum", "channel_trading"}
    best = rl.best_per_regime()

    for regime, expected in [("Bull", trend_strats),
                               ("Bear", reversion_strats),
                               ("Choppy", reversion_strats)]:
        strategy = best[regime][0]
        mark = "OK" if strategy in expected else "? unexpected - check signal logic"
        print(f"    {regime:8} best={strategy:30}  {mark}")

    ok_spread  = all(v > 0.05 for v in spreads.values())
    ok_updates = total_updates > 5000
    print(f"\n    Spread ok  (>0.05):  {'OK' if ok_spread  else 'NOT OK - run with smaller STEP_SIZE'}")
    print(f"    Updates ok (>5000):  {'OK' if ok_updates else 'NOT OK - too few - check data fetching'}")

    rl.save(OUTPUT_FILE)

    print("\n  NEXT STEPS AFTER THIS RUN")
    print(f"  1. Open {OUTPUT_FILE} and check q_table_by_regime")
    print("  2. Bull best should be a trend strategy (fibonacci/momentum/ema)")
    print("  3. Bear best should be a reversion strategy (mean_reversion/rsi_reversal)")
    print("  4. Update backend/quant/rl_strategy_selector.py to load this file on startup")
    print("  5. Change choose_strategy() to use regime-prefixed keys: 'Bull_strategy_name'")
    print("  6. Rerun bloomberg_kpi_test.py — Q-table section should show spread > 0.5")


# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\n  Bloomberg Quant - RL Q-Table Training")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Training period: {TRAIN_START} -> {TRAIN_END}")
    print(f"  Output: {OUTPUT_FILE}\n")
    train()
