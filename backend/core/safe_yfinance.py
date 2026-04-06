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
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List, Callable

# ─── Suppress YFinance Warnings ──────────────────────────────────────────────
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

# ─── In-memory cache ────────────────────────────────────────────────────────
_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes

# ─── Rate-limit delay between batch requests ─────────────────────────────────
_RATE_LIMIT_DELAY = 0.15  # seconds


def _cache_key(symbol: str, period: str, interval: str = "") -> str:
    return f"{symbol.upper()}:{period}:{interval}"


def _is_fresh(entry: Dict[str, Any]) -> bool:
    return time.time() - entry.get("cached_at", 0) < _CACHE_TTL_SECONDS


def safe_fetch_history(
    symbol: str,
    period: str = "7d",
    interval: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
    rate_limit: bool = False,
) -> Dict[str, Any]:
    """
    Safely fetch ticker history with caching.
    Supports fixed periods OR specific date ranges.
    """
    # Use a specific cache key for date ranges
    if start or end:
        key = f"RANGE:{symbol.upper()}:{start}:{end}:{interval}"
    else:
        key = _cache_key(symbol, period, interval)
        
    if key in _cache and _is_fresh(_cache[key]):
        return _cache[key]

    if rate_limit:
        time.sleep(_RATE_LIMIT_DELAY)

    try:
        ticker = yf.Ticker(symbol)
        
        if start or end:
            df = ticker.history(start=start, end=end, interval=interval)
        else:
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
    Safely fetch ticker info metadata with caching.
    """
    symbol = symbol.upper().strip()
    key = f"INFO:{symbol}"
    
    if key in _cache and _is_fresh(_cache[key]):
        return _cache[key]

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info:
            return {"status": "no_data", "data": {}}

        result = {"status": "ok", "data": info, "cached_at": time.time()}
        _cache[key] = result
        return result

    except Exception as e:
        logger.warning(f"[safe_yfinance] fetch_info({symbol}) failed: {e}")
        return {"status": "error", "error": str(e), "data": {}}


def safe_get_price(symbol: str) -> Optional[float]:
    """
    Safely get the current price for a symbol.
    """
    # 1. Check info first (fast)
    info_res = safe_fetch_info(symbol)
    if info_res["status"] == "ok":
        info = info_res["data"]
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        if price: return float(price)

    # 2. Fallback to short history
    hist_res = safe_fetch_history(symbol, period="5d")
    if hist_res["status"] == "ok":
        df = hist_res["data"]
        if df is not None and not df.empty:
            return float(df["Close"].iloc[-1])
            
    return None


def safe_fetch_candles(
    symbol: str,
    interval: str = "1d",
    period: str = "1mo",
    market: str = "us"
) -> List[Dict[str, Any]]:
    """
    Consolidated, safe candle fetching for all modules.
    Ensures market suffixes are handled and errors are caught.
    """
    # 1. Normalize and validate
    symbol = symbol.upper().strip()
    market = market.lower().strip()
    
    if market == "india" and not (symbol.endswith(".NS") or symbol.endswith(".BO")):
        symbol = f"{symbol}.NS"

    # 2. Fetch using history wrapper
    res = safe_fetch_history(symbol, period=period, interval=interval)
    if res["status"] != "ok" or res["data"] is None:
        return []

    df = res["data"]
    try:
        candles = []
        for idx, row in df.iterrows():
            candles.append({
                "date": idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                "open": round(float(row.get('Open', 0)), 2),
                "high": round(float(row.get('High', 0)), 2),
                "low": round(float(row.get('Low', 0)), 2),
                "close": round(float(row.get('Close', 0)), 2),
                "volume": int(row.get('Volume', 0))
            })
        return candles
    except Exception as e:
        logger.error(f"[safe_yfinance] Candle processing failed for {symbol}: {e}")
        return []


def calculate_indicators(symbol: str, range_period: str = "6mo", interval: str = "1d", market: str = "us") -> Dict[str, Any]:
    """
    Centralized technical indicator calculation.
    """
    symbol = symbol.upper().strip()
    if market.lower() == "india" and not (symbol.endswith(".NS") or symbol.endswith(".BO")):
        symbol = f"{symbol}.NS"

    # Fetch enough data for indicators (warmup)
    res = safe_fetch_history(symbol, period="1y", interval=interval)
    if res["status"] != "ok" or res["data"] is None:
        return {}

    df = res["data"]
    if len(df) < 20:
        return {}

    try:
        # RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMAs
        df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd_line'] = ema12 - ema26
        df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd_line'] - df['macd_signal']

        # Replace NaNs for JSON
        df = df.replace({np.nan: None})
        
        # Trim to requested period if needed (simple slice for now)
        # In a real app we'd filter by index date
        
        return {
            "dates": df.index.strftime('%Y-%m-%d').tolist(),
            "rsi": df['rsi'].tolist(),
            "macd": {
                "line": df['macd_line'].tolist(),
                "signal": df['macd_signal'].tolist(),
                "histogram": df['macd_hist'].tolist()
            },
            "ema": {
                "20": df['ema_20'].tolist(),
                "50": df['ema_50'].tolist(),
                "200": df['ema_200'].tolist()
            }
        }
    except Exception as e:
        logger.error(f"[safe_yfinance] Indicators failed for {symbol}: {e}")
        return {}


def safe_fetch_multiple_quotes(
    symbols: List[str], 
    max_workers: int = 15,
    validator: Optional[Callable[[str], bool]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    [OPTIMIZED] Fetch quotes for multiple symbols in parallel batches.
    """
    results = {}
    if not symbols:
        return results
        
    # Validation Layer
    if validator:
        valid_symbols = [s for s in symbols if validator(s)]
        if not valid_symbols:
            return {s: {"symbol": s, "error": "Filtered by validator"} for s in symbols}
        symbols = valid_symbols

    now = time.time()
    symbols_to_fetch = []
    
    for symbol in symbols:
        key = _cache_key(symbol, "7d")
        if key in _cache and _is_fresh(_cache[key]):
            results[symbol] = _cache[key].get("quote_data", {})
        else:
            symbols_to_fetch.append(symbol)
            
    if not symbols_to_fetch:
        return results

    # Smaller batches reduce the chance that a single slow ticker stalls the whole snapshot.
    batch_size = 5
    batches = [symbols_to_fetch[i:i + batch_size] for i in range(0, len(symbols_to_fetch), batch_size)]
    
    def fetch_batch(batch_symbols):
        try:
            data = yf.download(
                tickers=batch_symbols, 
                period="5d", 
                interval="1d", 
                group_by='ticker', 
                auto_adjust=True, 
                progress=False,
                timeout=6
            )
            
            batch_results = {}
            for symbol in batch_symbols:
                ticker_key = symbol.upper()
                try:
                    df = data[symbol] if len(batch_symbols) > 1 else data
                    df = df.dropna(subset=['Close'])
                    if df.empty:
                        res = {"symbol": ticker_key, "price": None, "change": None, "change_percent": None}
                    else:
                        closes = df['Close'].tolist()
                        price = closes[-1]
                        prev_close = closes[-2] if len(closes) >= 2 else price
                        change = price - prev_close
                        change_percent = (change / prev_close) * 100 if prev_close else 0
                        
                        res = {
                            "symbol": ticker_key,
                            "price": round(float(price), 2),
                            "change": round(float(change), 2),
                            "change_percent": round(float(change_percent), 2),
                            "timestamp": now
                        }
                    batch_results[symbol] = res
                except Exception:
                    batch_results[symbol] = {"symbol": ticker_key, "price": None, "change": None, "change_percent": None}
            return batch_results
        except Exception as e:
            return {s: {"symbol": s.upper(), "error": str(e)} for s in batch_symbols}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_batch = {executor.submit(fetch_batch, b): b for b in batches}
        for future in as_completed(future_to_batch):
            try:
                batch_res = future.result()
                for s, r in batch_res.items():
                    results[s] = r
                    if r.get("price") is not None:
                        cache_key = _cache_key(s, "7d")
                        _cache[cache_key] = {"status": "ok", "quote_data": r, "cached_at": now}
            except Exception as exc:
                logger.debug("Quote batch future failed: %s", exc)

    return results


def clear_cache():
    _cache.clear()
