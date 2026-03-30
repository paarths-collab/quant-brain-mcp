"""
Isolated strategy_adapter for backtest/core — self-contained copy.
Includes SMA Crossover, RSI Momentum, EMA Crossover, MACD, Breakout, 
Mean Reversion, and Momentum strategies all inline.
Modifying this file does NOT affect technical/ or any other module.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any


# ─────────────────────────────────────────
# BASE STRATEGY
# ─────────────────────────────────────────

class BaseStrategy:
    name: str = "base"
    parameters: Dict[str, Any] = {}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError


# ─────────────────────────────────────────
# SMA CROSSOVER
# ─────────────────────────────────────────

class SMACrossoverStrategy(BaseStrategy):
    name = "SMA Crossover"

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast = int(fast_period)
        self.slow = int(slow_period)
        self.parameters = {"fast_period": self.fast, "slow_period": self.slow}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["sma_fast"] = df["Close"].rolling(self.fast).mean()
        df["sma_slow"] = df["Close"].rolling(self.slow).mean()
        df["signal"] = 0
        df.loc[df["sma_fast"] > df["sma_slow"], "signal"] = 1
        df.loc[df["sma_fast"] < df["sma_slow"], "signal"] = -1
        return df


# ─────────────────────────────────────────
# RSI MOMENTUM
# ─────────────────────────────────────────

class RSIMomentumStrategy(BaseStrategy):
    name = "RSI Momentum"

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = int(period)
        self.oversold = int(oversold)
        self.overbought = int(overbought)
        self.parameters = {
            "period": self.period,
            "oversold": self.oversold,
            "overbought": self.overbought,
        }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.period).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["signal"] = 0
        df.loc[df["rsi"] < self.oversold, "signal"] = 1
        df.loc[df["rsi"] > self.overbought, "signal"] = -1
        return df


# ─────────────────────────────────────────
# EMA CROSSOVER
# ─────────────────────────────────────────

class EMACrossoverStrategy(BaseStrategy):
    name = "EMA Crossover"

    def __init__(self, fast_period: int = 12, slow_period: int = 26):
        self.fast = int(fast_period)
        self.slow = int(slow_period)
        self.parameters = {"fast_period": self.fast, "slow_period": self.slow}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["ema_fast"] = df["Close"].ewm(span=self.fast, adjust=False).mean()
        df["ema_slow"] = df["Close"].ewm(span=self.slow, adjust=False).mean()
        df["signal"] = 0
        df.loc[df["ema_fast"] > df["ema_slow"], "signal"] = 1
        df.loc[df["ema_fast"] < df["ema_slow"], "signal"] = -1
        return df


# ─────────────────────────────────────────
# MACD
# ─────────────────────────────────────────

class MACDStrategy(BaseStrategy):
    name = "MACD"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = int(fast)
        self.slow = int(slow)
        self.signal_period = int(signal)
        self.parameters = {"fast": self.fast, "slow": self.slow, "signal": self.signal_period}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        ema_fast = df["Close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["Close"].ewm(span=self.slow, adjust=False).mean()
        df["macd"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd"].ewm(span=self.signal_period, adjust=False).mean()
        df["signal"] = 0
        df.loc[df["macd"] > df["macd_signal"], "signal"] = 1
        df.loc[df["macd"] < df["macd_signal"], "signal"] = -1
        return df


# ─────────────────────────────────────────
# BREAKOUT
# ─────────────────────────────────────────

class BreakoutStrategy(BaseStrategy):
    name = "Breakout"

    def __init__(self, lookback: int = 20):
        self.lookback = int(lookback)
        self.parameters = {"lookback": self.lookback}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["upper"] = df["High"].rolling(self.lookback).max()
        df["lower"] = df["Low"].rolling(self.lookback).min()
        df["signal"] = 0
        df.loc[df["Close"] > df["upper"].shift(1), "signal"] = 1
        df.loc[df["Close"] < df["lower"].shift(1), "signal"] = -1
        return df


# ─────────────────────────────────────────
# MEAN REVERSION
# ─────────────────────────────────────────

class MeanReversionStrategy(BaseStrategy):
    name = "Mean Reversion"

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = int(period)
        self.std_dev = float(std_dev)
        self.parameters = {"period": self.period, "std_dev": self.std_dev}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["mean"] = df["Close"].rolling(self.period).mean()
        df["std"] = df["Close"].rolling(self.period).std()
        df["upper"] = df["mean"] + self.std_dev * df["std"]
        df["lower"] = df["mean"] - self.std_dev * df["std"]
        df["signal"] = 0
        df.loc[df["Close"] < df["lower"], "signal"] = 1   # oversold
        df.loc[df["Close"] > df["upper"], "signal"] = -1  # overbought
        return df


# ─────────────────────────────────────────
# MOMENTUM
# ─────────────────────────────────────────

class MomentumStrategy(BaseStrategy):
    name = "Momentum"

    def __init__(self, period: int = 10):
        self.period = int(period)
        self.parameters = {"period": self.period}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["momentum"] = df["Close"].pct_change(self.period)
        df["signal"] = 0
        df.loc[df["momentum"] > 0, "signal"] = 1
        df.loc[df["momentum"] < 0, "signal"] = -1
        return df


# ─────────────────────────────────────────
# REGISTRY & FACTORY
# ─────────────────────────────────────────

STRATEGY_REGISTRY = {
    "sma_crossover": SMACrossoverStrategy,
    "rsi_momentum": RSIMomentumStrategy,
    "ema_crossover": EMACrossoverStrategy,
    "macd": MACDStrategy,
    "breakout": BreakoutStrategy,
    "mean_reversion": MeanReversionStrategy,
    "momentum": MomentumStrategy,
}


def get_strategy(name: str, **params):
    """Factory — returns a strategy instance by name."""
    name = (name or "").lower().strip()
    if name not in STRATEGY_REGISTRY:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Strategy '{name}' not found. Available: {available}")
    return STRATEGY_REGISTRY[name](**params)


def get_available_strategies():
    """Return list of available strategies with default parameters."""
    result = []
    for name, cls in STRATEGY_REGISTRY.items():
        try:
            inst = cls()
            result.append({"id": name, "name": cls.name, "parameters": inst.parameters})
        except Exception:
            result.append({"id": name, "name": cls.name, "parameters": {}})
    return result
