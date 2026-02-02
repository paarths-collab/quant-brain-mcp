# # # File: utils/data_loader.py
# # # This is the final, master data utility for your entire application.



# import pandas as pd
# import yfinance as yf
# import logging
# from functools import lru_cache
# from pathlib import Path
# from typing import Dict, Any

# from backend.services.market_utils import get_market_config

# logger = logging.getLogger(__name__)

# # ------------------------------------------------
# # TICKER FORMATTING
# # ------------------------------------------------

# @lru_cache(maxsize=1)
# def _get_indian_symbols_set():
#     try:
#         project_root = Path(__file__).parent.parent
#         equity_file = project_root / "data" / "nifty500.csv"
#         if equity_file.exists():
#             df = pd.read_csv(equity_file)
#             return set(df['Symbol'].str.upper())
#     except Exception as e:
#         logger.error(e)
#     return set()

# def format_ticker(ticker: str, market: str) -> str:
#     ticker_upper = ticker.upper().replace(".NS", "")
#     market_upper = market.upper()

#     if market_upper in ["IN", "INDIA"]:
#         return f"{ticker_upper}.NS"

#     return ticker_upper


# # ------------------------------------------------
# # CORE DATA FETCHING
# # ------------------------------------------------

# def get_ohlcv(
#     ticker: str,
#     start: str,
#     end: str,
#     market: str,
# ) -> pd.DataFrame:
#     yf_ticker = format_ticker(ticker, market)
#     logger.info(f"Fetching OHLCV for {yf_ticker}")

#     df = yf.download(
#         yf_ticker,
#         start=start,
#         end=end,
#         progress=False,
#         auto_adjust=False
#     )

#     if df.empty:
#         raise ValueError(f"No market data for {ticker}")

#     if isinstance(df.columns, pd.MultiIndex):
#         df.columns = df.columns.get_level_values(0)

#     df.columns = [c.title() for c in df.columns]

#     required = ["Open", "High", "Low", "Close", "Volume"]
#     if not all(col in df.columns for col in required):
#         raise ValueError("Missing OHLCV columns")

#     return df[required]

# def get_history(
#     ticker: str,
#     start: str,
#     end: str,
#     market: str,
#     interval: str = "1d"
# ) -> pd.DataFrame:
#     yf_ticker = format_ticker(ticker, market)
#     df = yf.download(
#         yf_ticker,
#         start=start,
#         end=end,
#         interval=interval,
#         progress=False,
#         auto_adjust=True
#     )

#     if isinstance(df.columns, pd.MultiIndex):
#         df.columns = df.columns.get_level_values(0)

#     df.columns = [c.title() for c in df.columns]
#     return df

# def get_company_snapshot(ticker: str, market: str) -> Dict[str, Any]:
#     market_config = get_market_config(market)
#     yf_ticker = format_ticker(ticker, market)

#     stock = yf.Ticker(yf_ticker)
#     info = stock.info or {}

#     return {
#         "symbol": ticker,
#         "currency": market_config["currency_symbol"],
#         **info
#     }


# def get_benchmark_returns(symbol: str, start: str, end: str) -> pd.Series:
#     """
#     Fetches benchmark returns for comparison against strategy performance.
#     """
#     logger.info(f"Fetching benchmark data for {symbol} from {start} to {end}...")
#     try:
#         # Determine market for formatting if needed, defaulting to US for now or infer
#         # For simplicity, assume symbol is already correct or handled
#         # Benchmark usually indices like ^GSPC, ^NSEI
#         benchmark_data = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
#         if benchmark_data.empty:
#             logger.warning(f"No benchmark data found for {symbol}.")
#             return pd.Series(dtype=float)
            
#         return benchmark_data['Close'].pct_change().dropna()
        
#     except Exception as e:
#         logger.error(f"Failed to fetch benchmark data for {symbol}: {e}")
#         return pd.Series(dtype=float)

# # Alias for backward compatibility with strategies
# get_data = get_ohlcv

"""
Central Market Data Loader
--------------------------
Single trusted gateway for:
- OHLCV data
- Historical prices
- Returns
- Company fundamentals snapshot
- Benchmark returns

All strategies, engines, and APIs must use this module.
"""

import pandas as pd
import yfinance as yf
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

from backend.services.market_utils import get_market_config

logger = logging.getLogger(__name__)


# ============================================================
# TICKER FORMATTING (MARKET-AWARE)
# ============================================================

@lru_cache(maxsize=1)
def _get_indian_symbols_set() -> set:
    """
    Loads Indian equity symbols once (used for .NS suffix validation)
    """
    try:
        # services -> backend -> root
        project_root = Path(__file__).parent.parent.parent
        equity_file = project_root / "data" / "nifty500.csv"
        
        if equity_file.exists():
            df = pd.read_csv(equity_file)
            return set(df["Symbol"].astype(str).str.upper())
        else:
            logger.warning(f"Indian symbols file not found at: {equity_file}")
    except Exception as e:
        logger.error(f"Failed loading Indian symbols: {e}")
    return set()


def format_ticker(ticker: str, market: str) -> str:
    """
    Formats ticker symbol based on market conventions
    """
    ticker = ticker.upper().replace(".NS", "")
    market = market.upper()

    if market in {"IN", "INDIA"}:
        if ticker in _get_indian_symbols_set():
            return f"{ticker}.NS"

    return ticker


# ============================================================
# INTERNAL RAW FETCHERS (NOT CACHED)
# ============================================================

def _fetch_history_raw(
    ticker: str,
    start: str,
    end: str,
    market: str,
    interval: str,
    auto_adjust: bool,
) -> pd.DataFrame:

    yf_ticker = format_ticker(ticker, market)
    logger.info(f"Fetching history: {yf_ticker}")

    df = yf.download(
        yf_ticker,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=auto_adjust,
        progress=False,
    )

    if df.empty:
        raise ValueError(f"No market data for {ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [c.title() for c in df.columns]
    return df


# ============================================================
# CACHED MARKET DATA
# ============================================================

def _history_cache_key(
    ticker: str,
    start: str,
    end: str,
    market: str,
    interval: str,
    auto_adjust: bool,
) -> str:
    return f"{ticker}|{start}|{end}|{market}|{interval}|{auto_adjust}"


@lru_cache(maxsize=128)
def _cached_history(key: str) -> pd.DataFrame:
    ticker, start, end, market, interval, auto_adjust = key.split("|")
    return _fetch_history_raw(
        ticker=ticker,
        start=start,
        end=end,
        market=market,
        interval=interval,
        auto_adjust=auto_adjust == "True",
    )


def get_history(
    ticker: str,
    start: str,
    end: str,
    market: str,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Returns adjusted historical price data
    """
    key = _history_cache_key(ticker, start, end, market, interval, True)
    return _cached_history(key)


def get_ohlcv(
    ticker: str,
    start: str,
    end: str,
    market: str,
) -> pd.DataFrame:
    """
    Returns OHLCV data (non-adjusted, backtesting-ready)
    """
    key = _history_cache_key(ticker, start, end, market, "1d", False)
    df = _cached_history(key)

    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(df.columns):
        raise ValueError("Missing OHLCV columns")

    return df[list(required)]


# Backward compatibility alias
get_data = get_ohlcv


# ============================================================
# RETURNS HELPERS
# ============================================================

def get_returns(
    ticker: str,
    start: str,
    end: str,
    market: str,
) -> pd.Series:
    """
    Returns daily percentage returns
    """
    df = get_history(ticker, start, end, market)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)

    return df["Close"].pct_change().dropna()


def get_benchmark_returns(
    symbol: str,
    start: str,
    end: str,
) -> pd.Series:
    """
    Fetches benchmark returns (indices like ^GSPC, ^NSEI)
    """
    try:
        df = yf.download(
            symbol,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
        )
        if df.empty:
            return pd.Series(dtype=float)
        return df["Close"].pct_change().dropna()
    except Exception as e:
        logger.error(f"Benchmark fetch failed: {e}")
        return pd.Series(dtype=float)


# ============================================================
# COMPANY FUNDAMENTALS SNAPSHOT
# ============================================================

_ALLOWED_INFO_FIELDS = {
    "shortName",
    "sector",
    "industry",
    "marketCap",
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "dividendYield",
    "payoutRatio",
    "returnOnEquity",
    "debtToEquity",
    "revenueGrowth",
    "earningsGrowth",
}


def get_company_snapshot(
    ticker: str,
    market: str,
) -> Dict[str, Any]:
    """
    Returns a clean, stable subset of company fundamentals
    """
    market_cfg = get_market_config(market)
    yf_ticker = format_ticker(ticker, market)

    stock = yf.Ticker(yf_ticker)
    info = stock.info or {}

    filtered_info = {k: info.get(k) for k in _ALLOWED_INFO_FIELDS}

    return {
        "symbol": ticker,
        "market": market_cfg["market_name"],
        "currency": market_cfg["currency_symbol"],
        **filtered_info,
    }
