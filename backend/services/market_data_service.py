import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from backend.services.data_loader import get_history

def fetch_candles(
    symbol: str,
    interval: str = "1d",
    period: str = "1mo",
    start: Optional[str] = None,
    end: Optional[str] = None,
    market: str = "us"
) -> List[Dict[str, Any]]:
    """
    Fetch OHLCV candle data and return as list of dictionaries.
    
    Args:
        symbol: Stock ticker symbol
        interval: Data interval (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
        start: Start date (YYYY-MM-DD) - overrides period if provided
        end: End date (YYYY-MM-DD)
        market: Market identifier (us, india)
        
    Returns:
        List of candle dictionaries with keys: date, open, high, low, close, volume
    """
    try:
        # Use start/end if provided, otherwise use period
        if start and end:
            df = get_history(
                ticker=symbol,
                start=start,
                end=end,
                market=market,
                interval=interval
            )
        else:
            # Convert period to date range
            end_date = pd.Timestamp.now()
            
            if period == "1d":
                start_date = end_date - pd.DateOffset(days=1)
            elif period == "5d":
                start_date = end_date - pd.DateOffset(days=5)
            elif period == "1mo":
                start_date = end_date - pd.DateOffset(months=1)
            elif period == "3mo":
                start_date = end_date - pd.DateOffset(months=3)
            elif period == "6mo":
                start_date = end_date - pd.DateOffset(months=6)
            elif period == "1y":
                start_date = end_date - pd.DateOffset(years=1)
            elif period == "2y":
                start_date = end_date - pd.DateOffset(years=2)
            elif period == "5y":
                start_date = end_date - pd.DateOffset(years=5)
            else:
                start_date = end_date - pd.DateOffset(months=1)  # default
            
            df = get_history(
                ticker=symbol,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                market=market,
                interval=interval
            )
        
        if df.empty:
            return []
        
        # Convert DataFrame to list of dictionaries
        candles = []
        for idx, row in df.iterrows():
            candles.append({
                "date": idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                "open": float(row.get('Open', 0)),
                "high": float(row.get('High', 0)),
                "low": float(row.get('Low', 0)),
                "close": float(row.get('Close', 0)),
                "volume": int(row.get('Volume', 0))
            })
        
        return candles
        
    except Exception as e:
        print(f"Error fetching candles for {symbol}: {e}")
        return []


def get_market_overview() -> Dict[str, Any]:
    """
    Get overview of major market indices.
    
    Returns:
        Dictionary with major index data
    """
    try:
        indices = {
            "SPY": "S&P 500",
            "QQQ": "NASDAQ",
            "DIA": "Dow Jones",
            "^NSEI": "NIFTY 50",
            "^BSESN": "SENSEX"
        }
        
        overview = {}
        for symbol, name in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="5d")
                
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2] if len(hist) > 1 else current
                    change_pct = ((current - previous) / previous * 100) if previous else 0
                    
                    overview[symbol] = {
                        "name": name,
                        "price": float(current),
                        "change_pct": float(change_pct),
                        "volume": int(hist['Volume'].iloc[-1])
                    }
            except Exception:
                continue
        
        return overview
        
    except Exception as e:
        print(f"Error fetching market overview: {e}")
        return {}


def get_current_price(ticker: str) -> float:
    try:
        if not ticker: return 0.0
        # Simple normalization for common cases if needed, but relying on yf for now
        ticker = ticker.upper().strip()
        stock = yf.Ticker(ticker)
        price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice') or stock.info.get('previousClose')
        return float(price) if price else 0.0
    except Exception:
        return 0.0

# Standalone function as expected by sector_intel.py
def calculate_indicators(ticker: str, range: str = "6mo", interval: str = "1d") -> dict:
    try:
        # Calculate dates based on range
        end_date = pd.Timestamp.now()
        start_date = end_date - pd.DateOffset(months=6) # default
        
        if range == "1mo": 
            start_date = end_date - pd.DateOffset(months=1)
        elif range == "3mo": 
            start_date = end_date - pd.DateOffset(months=3)
        elif range == "1y": 
            start_date = end_date - pd.DateOffset(years=1)
        elif range == "2y":
            start_date = end_date - pd.DateOffset(years=2)
        elif range == "5y":
            start_date = end_date - pd.DateOffset(years=5)
            
        # Add buffer for indicators warmup (e.g. 200 EMA needs 200+ days)
        start_with_buffer = start_date - pd.DateOffset(days=300) 
        
        # Fetch data
        df = get_history(
            ticker, 
            start=start_with_buffer.strftime('%Y-%m-%d'), 
            end=end_date.strftime('%Y-%m-%d'), 
            market="US", # Defaulting to US for now, or infer from ticker
            interval=interval
        )
        
        if df.empty:
            return {}

        # --- Indicators ---
        
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
        
        # MACD (12, 26, 9)
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd_line'] = ema12 - ema26
        df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd_line'] - df['macd_signal']
        
        # ATR (14)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # VWAP
        # Simple cumulative VWAP from start of data
        df['vwap'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()

        # Trim to requested range
        mask = (df.index >= start_date)
        result_df = df.loc[mask].copy() # Copy to avoid SettingWithCopy
        
        # Replace NaNs with None for JSON serialization
        result_df = result_df.replace({np.nan: None})
        
        dates = result_df.index.strftime('%Y-%m-%d').tolist()
        
        return {
            "dates": dates,
            "rsi": result_df['rsi'].tolist(),
            "macd": {
                "line": result_df['macd_line'].tolist(),
                "signal": result_df['macd_signal'].tolist(),
                "histogram": result_df['macd_hist'].tolist()
            },
            "ema": {
                "20": result_df['ema_20'].tolist(),
                "50": result_df['ema_50'].tolist(),
                "200": result_df['ema_200'].tolist()
            },
            "atr": result_df['atr'].tolist(),
            "vwap": result_df['vwap'].tolist()
        }
            
    except Exception as e:
        print(f"Error calculating indicators for {ticker}: {e}")
        return {}


class MarketDataService:

    def normalize_ticker(self, ticker: str, market: str = "us") -> str:
        """
        Normalizes ticker based on market.
        - India: Appends .NS if missing
        - USA: returns as is
        """
        if not ticker:
            return ticker
            
        ticker = ticker.upper().strip()
        
        if market.lower() == "india":
            if not (ticker.endswith(".NS") or ticker.endswith(".BO")):
                return f"{ticker}.NS"
                
        return ticker

    def get_history(self, ticker):
        return yf.Ticker(ticker).history(period="6mo")

    def get_fundamentals(self, ticker):
        return yf.Ticker(ticker).info
