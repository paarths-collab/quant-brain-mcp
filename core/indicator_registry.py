"""Explicit allowlist of curated indicators exposed through grouped MCP tools.

This is the single source of truth for the public indicator surface:
38 core indicators in 6 groups. Everything else under tools/indicators/
stays importable for research but is NOT exposed as an MCP tool.
"""

from __future__ import annotations

import importlib
from typing import Iterator

# group -> {"tool": mcp_tool_name, "indicators": {key: (module_path, func_name)}}
INDICATOR_GROUPS: dict[str, dict] = {
    "momentum": {
        "tool": "analyze_momentum",
        "indicators": {
            "rsi": ("tools.indicators.momentum.rsi", "get_rsi"),
            "macd": ("tools.indicators.momentum.macd", "get_macd"),
            "roc": ("tools.indicators.momentum.roc", "get_roc"),
            "cci": ("tools.indicators.momentum.cci", "get_cci"),
            "stoch": ("tools.indicators.momentum.stoch", "get_stoch"),
            "stochrsi": ("tools.indicators.momentum.stochrsi", "get_stochrsi"),
            "tsi": ("tools.indicators.momentum.tsi", "get_tsi"),
            "willr": ("tools.indicators.momentum.willr", "get_willr"),
        },
    },
    "technical_levels": {
        "tool": "analyze_technical_levels",
        "indicators": {
            "sma": ("tools.indicators.overlap.sma", "get_sma"),
            "ema": ("tools.indicators.overlap.ema", "get_ema"),
            "hma": ("tools.indicators.overlap.hma", "get_hma"),
            "kama": ("tools.indicators.overlap.kama", "get_kama"),
            "ichimoku": ("tools.indicators.overlap.ichimoku", "get_ichimoku"),
            "supertrend": ("tools.indicators.overlap.supertrend", "get_supertrend"),
            "vwap": ("tools.indicators.overlap.vwap", "get_vwap"),
            "vwma": ("tools.indicators.overlap.vwma", "get_vwma"),
        },
    },
    "trend": {
        "tool": "analyze_trend",
        "indicators": {
            "adx": ("tools.indicators.trend.adx", "get_adx"),
            "aroon": ("tools.indicators.trend.aroon", "get_aroon"),
            "chop": ("tools.indicators.trend.chop", "get_chop"),
            "psar": ("tools.indicators.trend.psar", "get_psar"),
            "vortex": ("tools.indicators.trend.vortex", "get_vortex"),
            "zigzag": ("tools.indicators.trend.zigzag", "get_zigzag"),
        },
    },
    "volatility": {
        "tool": "analyze_volatility",
        "indicators": {
            "atr": ("tools.indicators.volatility.atr", "get_atr"),
            "bbands": ("tools.indicators.volatility.bbands", "get_bbands"),
            "donchian": ("tools.indicators.volatility.donchian", "get_donchian"),
            "kc": ("tools.indicators.volatility.kc", "get_kc"),
            "stdev": ("tools.indicators.volatility.stdev", "get_stdev"),
            "ui": ("tools.indicators.volatility.ui", "get_ui"),
        },
    },
    "volume": {
        "tool": "analyze_volume",
        "indicators": {
            "obv": ("tools.indicators.volume.obv", "get_obv"),
            "cmf": ("tools.indicators.volume.cmf", "get_cmf"),
            "mfi": ("tools.indicators.volume.mfi", "get_mfi"),
            "ad": ("tools.indicators.volume.ad", "get_ad"),
            "pvt": ("tools.indicators.volume.pvt", "get_pvt"),
        },
    },
    "statistics": {
        "tool": "analyze_statistics",
        "indicators": {
            "log_return": ("tools.indicators.misc.log_return", "get_log_return"),
            "zscore": ("tools.indicators.misc.zscore", "get_zscore"),
            "skew": ("tools.indicators.misc.skew", "get_skew"),
            "kurtosis": ("tools.indicators.misc.kurtosis", "get_kurtosis"),
            "entropy": ("tools.indicators.misc.entropy", "get_entropy"),
        },
    },
}


def _resolve(module_path: str, func_name: str):
    """Lazily import an indicator callable (keeps server cold-start fast)."""
    return getattr(importlib.import_module(module_path), func_name)


def iter_all_indicators() -> Iterator[tuple[str, str, str, str]]:
    """Yield (key, module_path, func_name, group) for every allowlisted indicator."""
    for group, spec in INDICATOR_GROUPS.items():
        for key, (module_path, func_name) in spec["indicators"].items():
            yield key, module_path, func_name, group


def run_group(group: str, ticker: str, indicators: list[str] | None = None) -> dict:
    """Run all (or a subset of) indicators in a group against one ticker.

    Data is fetched once; each indicator runs isolated so a single failure
    cannot take down the whole group.
    """
    from core import data_loader
    from utils.serializer import serialize_output

    spec = INDICATOR_GROUPS[group]
    available = spec["indicators"]

    if indicators:
        requested = [str(i).strip().lower() for i in indicators]
    else:
        requested = list(available)
    unknown = [k for k in requested if k not in available]
    selected = [k for k in requested if k in available]

    df, err = data_loader.fetch_data(ticker)
    if err:
        return {
            "ticker": ticker,
            "group": group,
            "error": err,
            "indicators": {},
            "unknown_indicators": unknown,
        }

    results: dict[str, object] = {}
    for key in selected:
        module_path, func_name = available[key]
        try:
            results[key] = serialize_output(_resolve(module_path, func_name)(df))
        except Exception as exc:
            results[key] = {"error": f"{key} failed: {exc}"}

    return {
        "ticker": ticker,
        "group": group,
        "indicators": results,
        "unknown_indicators": unknown,
    }
