# File: utils/data_loader.py
# Master data utility for FastAPI/HTML application

import json
import pandas as pd
import yfinance as yf
import ta
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

# --- Local Imports ---
from .market_utils import get_market_config

# --- Module Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===================================================================
#                      TICKER FORMATTING
# ===================================================================

@lru_cache(maxsize=1)
def _get_indian_symbols_set():
    """Internal function to load Indian stock symbols for formatting."""
    try:
        backend_root = Path(__file__).resolve().parents[3]
        equity_file = backend_root / "data" / "nifty500.json"
        if equity_file.exists():
            with equity_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return set(
                item["Symbol"].upper()
                for item in data
                if isinstance(item, dict) and item.get("Symbol")
            )
    except Exception as e:
        logger.error(f"Could not load Indian symbols file: {e}")
    return set()

def format_ticker(ticker: str, market: str) -> str:
    """
    Public function to format a ticker symbol according to its market for yfinance.
    """
    try:
        ticker_upper = ticker.upper().replace(".NS", "")
        market_upper = market.upper()

        if market_upper in ['IN', 'INDIA']:
            # Append .NS for tickers in the Indian market
            if ticker_upper in _get_indian_symbols_set():
                return f"{ticker_upper}.NS"
        # For other markets like US, EU, JP, etc., yfinance typically uses the ticker as is.
        # Add specific formatting for other markets here if needed in the future.
        return ticker_upper
    except Exception as e:
        logger.error(f"Could not format ticker '{ticker}' for market '{market}': {e}")
        return ticker

# ===================================================================
#                       CORE DATA FUNCTIONS
# ===================================================================

def get_data(ticker: str, start: str, end: str, market: str) -> pd.DataFrame:
    """
    Fetches and formats data for a specific market, ready for the backtesting.py library.
    """
    logger.info(f"Fetching data for {ticker} ({market}) from {start} to {end}.")
    try:
        yf_ticker = format_ticker(ticker, market)
        df = yf.download(yf_ticker, start=start, end=end, progress=False, auto_adjust=False)

        if df.empty:
            logger.error(f"No data found for ticker {ticker} in the {market} market.")
            return pd.DataFrame()

        # Handle MultiIndex columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Standardize column names to Title Case for backtesting.py compatibility
        df.columns = [str(col).title() for col in df.columns]

        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            logger.error(f"Data for {ticker} is missing required OHLCV columns.")
            return pd.DataFrame()

        return df[required_cols]
    except Exception as e:
        logger.error(f"An error occurred while fetching data for {ticker}: {e}")
        return pd.DataFrame()

def get_history(ticker: str, start: str, end: str, market: str, interval: str = "1d") -> pd.DataFrame:
    """Fetches general historical market data."""
    yf_ticker = format_ticker(ticker, market)
    try:
        df = yf.download(yf_ticker, start=start, end=end, interval=interval, progress=False, auto_adjust=True)
        
        # Handle MultiIndex columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Standardize column names to Title Case to match the expected format
        df.columns = [str(col).title() for col in df.columns]
        
        return df
    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {e}")
        return pd.DataFrame()

def get_company_snapshot(ticker: str, market: str) -> Dict[str, Any]:
    """Returns a snapshot of a company's key fundamentals with correct currency."""
    market_config = get_market_config(market)
    yf_ticker = format_ticker(ticker, market)
    try:
        stock = yf.Ticker(yf_ticker)
        info = stock.info
        return {"currencySymbol": market_config["currency_symbol"], **info}
    except Exception as e:
        logger.error(f"Error fetching company snapshot for {ticker}: {e}")
        return {"symbol": ticker, "error": str(e)}

# ===================================================================
#                       DATA ENRICHMENT
# ===================================================================

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Appends a curated set of key technical indicators to an OHLCV DataFrame."""
    if df.empty or 'Close' not in df.columns or 'Volume' not in df.columns:
        return df
    
    try:
        # This function uses the 'ta' library to add indicators.
        # Ensure you have it installed: pip install ta
        df = ta.add_all_ta_features(
            df, open="Open", high="High", low="Low", close="Close", volume="Volume", fillna=True
        )
        logger.info("Successfully added technical indicators.")
        return df
    except Exception as e:
        logger.error(f"Error adding technical indicators: {e}")
        # Fallback: add basic indicators one by one
        try:
            if 'Close' in df.columns:
                df['momentum_rsi'] = ta.momentum.rsi(close=df['Close'], window=14, fillna=True)
            if 'High' in df.columns and 'Low' in df.columns and 'Close' in df.columns:
                df['volatility_bbh'] = ta.volatility.bollinger_hband(close=df['Close'], window=20, window_dev=2, fillna=True)
                df['volatility_bbl'] = ta.volatility.bollinger_lband(close=df['Close'], window=20, window_dev=2, fillna=True)
            if 'Close' in df.columns:
                df['trend_sma_fast'] = ta.trend.sma_indicator(close=df['Close'], window=50, fillna=True)
                df['trend_sma_slow'] = ta.trend.sma_indicator(close=df['Close'], window=200, fillna=True)
            if 'Close' in df.columns:
                df['trend_macd'] = ta.trend.macd(close=df['Close'], window_slow=26, window_fast=12, fillna=True)
                df['trend_macd_signal'] = ta.trend.macd_signal(close=df['Close'], window_slow=26, window_fast=12, window_sign=9, fillna=True)
            if 'Close' in df.columns and 'Volume' in df.columns:
                df['volume_obv'] = ta.volume.on_balance_volume(close=df['Close'], volume=df['Volume'], fillna=True)
        except Exception as e2:
            logger.error(f"Fallback method also failed: {e2}")
        return df
