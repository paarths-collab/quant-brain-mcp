import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from .market_data import market_service

logger = logging.getLogger(__name__)

class TechnicalAnalysisService:
    """
    High-performance technical analysis service.
    Consolidates indicator calculations (RSI, EMA, MACD) into one location for all modules.
    """

    def calculate_indicators(
        self, 
        ticker: str, 
        range_period: str = "6mo", 
        interval: str = "1d", 
        market: str = "us"
    ) -> Dict[str, Any]:
        """
        Calculate a comprehensive set of technical indicators for a given ticker.
        """
        try:
            # 1. Ticker Normalization
            ticker = market_service.normalize_ticker(ticker, market)
            
            # 2. Fetch history with buffer for indicator warmup
            # (e.g., 200 EMA needs 200+ data points)
            df = market_service.get_history(ticker, period="2y", interval=interval)
            
            if df.empty:
                return {}

            # --- Technical Indicators ---
            
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
            
            # VWAP (Approximate)
            df['vwap'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()

            # --- Truncate to requested range ---
            # Map requested period to data points
            limit_map = {
                "1mo": 22,
                "3mo": 66,
                "6mo": 126,
                "1y": 252,
                "2y": 504,
                "5y": 1260
            }
            limit = limit_map.get(range_period, 126)
            result_df = df.tail(limit).copy()
            
            # Handle NaN for JSON serialization
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
            logger.error(f"Error calculating indicators for {ticker}: {e}")
            return {}

    def compute_signals(self, df: pd.DataFrame, mom_period: int = 14, vol_period: int = 20) -> Optional[Dict[str, Any]]:
        """
        [CENTRALIZED] Compute momentum and volume signals for scanners.
        Ported from ScreenerService for architectural consistency.
        """
        try:
            if df.empty or len(df) < mom_period + vol_period:
                return None

            close = df["Close"].squeeze()
            volume = df["Volume"].squeeze()

            # ROC (Rate of Change)
            roc = ((close.iloc[-1] - close.iloc[-mom_period]) / close.iloc[-mom_period]) * 100
            
            # Volume Ratio (relative to MA)
            avg_volume = volume.iloc[-vol_period - 1 : -1].mean()
            vol_ratio = volume.iloc[-1] / avg_volume if avg_volume > 0 else 0
            
            latest_close = float(close.iloc[-1])
            sma20 = float(close.iloc[-vol_period:].mean())
            
            return {
                "close": round(latest_close, 2),
                "roc_pct": round(float(roc), 2),
                "vol_ratio": round(float(vol_ratio), 2),
                "trend": "up" if latest_close > sma20 else "down",
                "as_of": df.index[-1].strftime("%Y-%m-%d %H:%M") if hasattr(df.index[-1], 'strftime') else str(df.index[-1]),
            }
        except Exception as e:
            logger.error(f"Error computing signals: {e}")
            return None

# Singleton instance for platform-wide use
technical_service = TechnicalAnalysisService()
