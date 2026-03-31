"""
safe_yfinance.py — Centralized, fail-safe Yahoo Finance wrapper.

All backend modules should import from here instead of calling
yf.Ticker(...) directly. This prevents crashes from:
  - Empty DataFrames (delisted / no data)
  - Rate limit exceptions
  - yfinance internal errors

Usage:
    from backend.core.safe_yfinance import safe_fetch_history, safe_fetch_info

    res = safe_fetch_history("AAPL")
    if res["status"] != "ok":
        return None  # or whatever fallback you need
    df = res["data"]
    price = float(df["Close"].iloc[-1])
"""

import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ─── In-memory cache ────────────────────────────────────────────────────────
# { "AAPL:7d": {"status": "ok", "data": <df>, "cached_at": <timestamp>} }
_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes

# ─── Rate-limit delay between batch requests ─────────────────────────────────
_RATE_LIMIT_DELAY = 0.15  # seconds


def _cache_key(symbol: str, period: str) -> str:
    return f"{symbol.upper()}:{period}"


def _is_fresh(entry: Dict[str, Any]) -> bool:
    import time as _time
    return _time.time() - entry.get("cached_at", 0) < _CACHE_TTL_SECONDS


def safe_fetch_history(
    symbol: str,
    period: str = "7d",
    interval: str = "1d",
    rate_limit: bool = False,
) -> Dict[str, Any]:
    """
    Safely fetch ticker history. Returns:
        {"status": "ok",       "data": <DataFrame>}
        {"status": "no_data",  "data": None}
        {"status": "error",    "error": "<message>", "data": None}
    """
    key = _cache_key(symbol, period)
    if key in _cache and _is_fresh(_cache[key]):
        return _cache[key]

    if rate_limit:
        time.sleep(_RATE_LIMIT_DELAY)

    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df is None or df.empty:
            result = {"status": "no_data", "data": None}
        else:
            result = {"status": "ok", "data": df, "cached_at": time.time()}
            _cache[key] = result

        return result

    except Exception as e:
        logger.warning(f"[safe_yfinance] fetch_history({symbol}) failed: {e}")
        return {"status": "error", "error": str(e), "data": None}


def safe_fetch_info(symbol: str) -> Dict[str, Any]:
    """
    Safely fetch ticker info dict. Returns:
        {"status": "ok",      "data": <dict>}
        {"status": "no_data", "data": {}}
        {"status": "error",   "error": "<message>", "data": {}}
    """
    key = _cache_key(symbol, "info")
    if key in _cache and _is_fresh(_cache[key]):
        return _cache[key]

    try:
        import yfinance as yf
        info = yf.Ticker(symbol).info or {}
        if not info or info.get("trailingPegRatio") is None and len(info) < 5:
            return {"status": "no_data", "data": {}}
        result = {"status": "ok", "data": info, "cached_at": time.time()}
        _cache[key] = result
        return result

    except Exception as e:
        logger.warning(f"[safe_yfinance] fetch_info({symbol}) failed: {e}")
        return {"status": "error", "error": str(e), "data": {}}


def safe_get_price(symbol: str) -> Optional[float]:
    """
    Returns the latest closing price or None on any failure.
    Convenience wrapper for single-value lookups.
    """
    res = safe_fetch_history(symbol, period="5d")
    if res["status"] != "ok":
        return None
    try:
        return float(res["data"]["Close"].dropna().iloc[-1])
    except Exception:
        return None


def safe_get_change_pct(symbol: str, period: str = "5d") -> Optional[float]:
    """
    Returns the % change over the period or None on failure.
    """
    res = safe_fetch_history(symbol, period=period)
    if res["status"] != "ok":
        return None
    try:
        closes = res["data"]["Close"].dropna()
        if len(closes) < 2:
            return None
        return float((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0] * 100)
    except Exception:
        return None


def clear_cache():
    """Force-clear the in-memory cache (useful for testing)."""
    _cache.clear()
