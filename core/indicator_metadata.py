"""Reproducibility metadata for the curated daily-bar indicators.

Defaults below are verified against the pinned pandas-ta implementation, not
its sometimes inconsistent docstrings. Wrapper defaults override library defaults.
"""
from __future__ import annotations

from copy import deepcopy
from importlib.metadata import PackageNotFoundError, version
import inspect
import math
from numbers import Real

# Parameters not explicitly passed by the thin wrappers. Update alongside the
# pandas-ta pin; preserve engine versions in each response for reproducibility.
LIBRARY_DEFAULTS = {
    "rsi": {"scalar": 100, "mamode": "rma", "drift": 1},
    "macd": {"asmode": False, "mamode": "ema"},
    "roc": {"scalar": 100},
    "cci": {},
    "stoch": {"smooth_k": 3, "mamode": "sma"},
    "stochrsi": {"rsi_length": 14, "k": 3, "d": 3, "mamode": "sma"},
    "tsi": {"fast": 13, "slow": 25, "signal": 13, "scalar": 100, "mamode": "ema", "drift": 1},
    "willr": {},
    "sma": {},
    "ema": {"presma": True, "adjust": False},
    "hma": {"mamode": "wma"},
    "kama": {"fast": 2, "slow": 30, "mamode": "sma", "drift": 1},
    "ichimoku": {"tenkan": 9, "kijun": 26, "senkou": 52, "include_chikou": True, "lookahead": True},
    "supertrend": {"atr_length": 7, "atr_mamode": "rma"},
    "vwap": {"anchor": "D", "bands": None},
    "vwma": {},
    "adx": {"signal_length": 14, "adxr_length": 2, "scalar": 100, "mamode": "rma", "drift": 1, "tvmode": False},
    "aroon": {"scalar": 100},
    "chop": {"atr_length": 1, "scalar": 100, "ln": False, "drift": 1},
    "psar": {"af": 0.02, "af0": 0.02, "max_af": 0.2},
    "vortex": {"drift": 1},
    "zigzag": {"legs": 10, "deviation": 5.0, "backtest": False},
    "atr": {"mamode": "rma", "drift": 1, "prenan": False, "percent": False},
    "bbands": {"ddof": 1, "mamode": "sma"},
    "donchian": {},
    "kc": {"tr": True, "mamode": "ema"},
    "stdev": {"ddof": 1},
    "ui": {"scalar": 100, "everget": False},
    "obv": {},
    "cmf": {"open_": None},
    "mfi": {"drift": 1},
    "ad": {"open_": None},
    "pvt": {"drift": 1, "roc_scalar": 100},
    "log_return": {"length": 1, "cumulative": False},
    "zscore": {"length": 30, "std": 1, "ddof": 1},
    "skew": {"length": 30},
    "kurtosis": {"length": 30},
    "entropy": {"length": 10, "base": 2},
}

UNITS = {
    "rsi": "oscillator points (0 to 100)", "macd": "price units",
    "roc": "percent", "cci": "dimensionless", "stoch": "oscillator points (0 to 100)",
    "stochrsi": "oscillator points (0 to 100)", "tsi": "oscillator points (-100 to 100)",
    "willr": "oscillator points (-100 to 0)",
    **{k: "price units" for k in ("sma", "ema", "hma", "kama", "ichimoku", "vwap", "vwma", "atr", "donchian", "kc", "stdev")},
    "supertrend": {"SUPERT": "price units", "SUPERTd": "direction (+1 or -1)", "SUPERTl": "price units", "SUPERTs": "price units"},
    "adx": "oscillator points", "aroon": "oscillator points", "chop": "oscillator points",
    "psar": {"PSARl": "price units", "PSARs": "price units", "PSARaf": "acceleration fraction", "PSARr": "reversal flag (0 or 1)"},
    "vortex": "ratio", "zigzag": {"ZIGZAGs": "swing direction", "ZIGZAGv": "price units", "ZIGZAGd": "percent"},
    "bbands": {"BBL": "price units", "BBM": "price units", "BBU": "price units", "BBB": "percent", "BBP": "fraction"},
    "ui": "percentage points", "obv": "cumulative volume units", "cmf": "fraction",
    "mfi": "oscillator points (0 to 100)", "ad": "cumulative volume units",
    "pvt": "cumulative volume units multiplied by percent return",
    "log_return": "natural log ratio", "zscore": "standard deviations", "skew": "dimensionless",
    "kurtosis": "dimensionless excess kurtosis", "entropy": "bits",
}

NOTES = {
    "vwap": "Daily bars with daily reset: this is typical price per daily bar, not intraday execution VWAP.",
    "ichimoku": "Chikou is shifted backward and can contain future information relative to its label. Forward-cloud frame is omitted; do not use this output directly for backtesting.",
    "zigzag": "Sparse historical pivots may repaint; no pivot in the last 10 bars does not mean a flat trend.",
    "skew": "Computed on close price levels, not returns; does not measure return-tail risk.",
    "kurtosis": "Computed on close price levels, not returns; does not measure return-tail risk.",
    "entropy": "Rolling entropy of normalized close prices, not a forecast of market unpredictability.",
    "obv": "Cumulative result depends on the requested history start.",
    "ad": "Cumulative result depends on the requested history start.",
    "pvt": "Cumulative result depends on the requested history start; pandas-ta uses percent ROC, not fractional ROC.",
}


def _version(package):
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def indicator_metadata(key, func):
    parameters = {"offset": 0, **deepcopy(LIBRARY_DEFAULTS[key])}
    parameters.update({
        name: p.default for name, p in inspect.signature(func).parameters.items()
        if p.default is not inspect.Parameter.empty
    })
    if key == "bbands":
        parameters["lower_std"] = parameters["upper_std"] = parameters.pop("std")
    if key == "donchian":
        parameters["lower_length"] = parameters["upper_length"] = parameters.pop("length")
    notes = [NOTES[key]] if key in NOTES else []
    if key in {"bbands", "stdev", "zscore"}:
        import pandas_ta as ta
        if ta.Imports.get("talib"):
            parameters["ddof"] = 0
            notes.append("TA-Lib uses population standard deviation (ddof=0); the native pandas-ta default is ddof=1.")
    return {
        "parameters": parameters,
        "window_unit": "bars",
        "output_units": deepcopy(UNITS[key]),
        "implementation": "local CCI formula" if key == "cci" else "pandas-ta",
        "notes": notes,
    }


def finite_value_count(value):
    if isinstance(value, dict):
        return sum(finite_value_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(finite_value_count(v) for v in value)
    return int(isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value))


def history_metadata(df, period):
    import pandas_ta as ta

    timezone = getattr(df.index, "tz", None)
    attrs = df.attrs
    return {
        "source": "yfinance",
        "currency": None,
        "currency_status": "Not supplied by the OHLCV history download; price units use the instrument quote currency.",
        "resolved_ticker": attrs.get("resolved_ticker"),
        "history_period": period,
        "interval": "1d",
        "input_rows": len(df),
        "data_start": str(df.index.min()) if len(df) else None,
        "data_end": str(df.index.max()) if len(df) else None,
        "index_timezone": str(timezone) if timezone is not None else None,
        "timestamp_semantics": "Daily bar labels, not verified exchange close timestamps. Naive dates have no supplied timezone.",
        "retrieved_at": attrs.get("retrieved_at"),
        "market_timestamp": None,
        "market_status": "unknown",
        "latest_bar_complete": None,
        "freshness": "unknown",
        "adjustment": {"auto_adjust": True, "prices": "split and dividend adjusted OHLC via yfinance", "volume": "provider supplied"},
        "returned_tail_bars": 10,
        "engine_versions": {"pandas-ta": _version("pandas-ta"), "pandas": _version("pandas"), "yfinance": _version("yfinance"), "TA-Lib": _version("TA-Lib")},
        "talib_available": bool(ta.Imports.get("talib")),
        "backend_policy": "pandas-ta may use TA-Lib for supported indicators when installed; otherwise its native implementation. CCI uses the local formula.",
    }
