import yfinance as yf
import pandas as pd
import ta
import math
from typing import List, Dict, Optional

def fetch_candles(symbol: str, interval: str = "1d", period: str = "1y", start: Optional[str] = None, end: Optional[str] = None) -> List[Dict]:
    """
    Fetches OHLCV data from yfinance and formats it for D3 charts.
    """
    try:
        ticker = yf.Ticker(symbol)
        # yfinance period options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        if start and end:
            df = ticker.history(start=start, end=end, interval=interval)
        else:
            df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            return []

        # Reset index to get Date as a column
        df.reset_index(inplace=True)
        
        if pd.api.types.is_datetime64_any_dtype(df['Date']):
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        else:
            df['Date'] = df['Date'].astype(str).str[:10]

        records = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict(orient="records")
        
        # Rename keys to lower case if needed or keep Title Case. 
        # D3 usually likes clear properties. Let's standardize to lowercase.
        cleaned_records = []
        for r in records:
            cleaned_records.append({
                "date": r['Date'],
                "open": r['Open'],
                "high": r['High'],
                "low": r['Low'],
                "close": r['Close'],
                "volume": r['Volume']
            })
            
        return cleaned_records
    except Exception as e:
        print(f"Error fetching candles for {symbol}: {e}")
        return []

def calculate_indicators(symbol: str, period: str = "1y", interval: str = "1d") -> Dict:
    """
    Calculates technical indicators: RSI, MACD, EMA(20, 50, 200), ATR.
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            return {}

        # Fill NaN data if any
        close = df['Close']
        high = df['High']
        low = df['Low']

        # RSI
        df['RSI'] = ta.momentum.RSIIndicator(close, window=14).rsi()

        # MACD
        macd = ta.trend.MACD(close)
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Hist'] = macd.macd_diff()

        # EMA
        df['EMA_20'] = ta.trend.EMAIndicator(close, window=20).ema_indicator()
        df['EMA_50'] = ta.trend.EMAIndicator(close, window=50).ema_indicator()
        df['EMA_200'] = ta.trend.EMAIndicator(close, window=200).ema_indicator()

        # ATR
        df['ATR'] = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
        
        # VWAP (Need Volume)
        df['VWAP'] = ta.volume.VolumeWeightedAveragePrice(high, low, close, df['Volume'], window=14).volume_weighted_average_price()

        # Format for frontend response
        # We need to align the indicators with dates
        df.reset_index(inplace=True)
        df['Date'] = df['Date'].astype(str)
        
        # Handle NaNs and infinities (replace with None)
        df = df.where(pd.notnull(df), None)
        df = df.replace([float("inf"), float("-inf")], None)

        def _clean_list(values):
            cleaned = []
            for v in values:
                if v is None:
                    cleaned.append(None)
                else:
                    try:
                        fv = float(v)
                        cleaned.append(fv if math.isfinite(fv) else None)
                    except Exception:
                        cleaned.append(None)
            return cleaned

        indicators = {
            "dates": df['Date'].tolist(),
            "rsi": _clean_list(df['RSI'].tolist()),
            "macd": {
                "line": _clean_list(df['MACD'].tolist()),
                "signal": _clean_list(df['MACD_Signal'].tolist()),
                "histogram": _clean_list(df['MACD_Hist'].tolist())
            },
            "ema": {
                "20": _clean_list(df['EMA_20'].tolist()),
                "50": _clean_list(df['EMA_50'].tolist()),
                "200": _clean_list(df['EMA_200'].tolist())
            },
            "atr": _clean_list(df['ATR'].tolist()),
            "vwap": _clean_list(df['VWAP'].tolist())
        }
        
        return indicators

    except Exception as e:
        print(f"Error calculating indicators for {symbol}: {e}")
        return {}

def get_market_overview() -> List[Dict]:
    """
    Fetches real-time(ish) data for major indices: S&P 500, Nasdaq, Dow, Russell 2000.
    """
    indices = {
        "^GSPC": "S&P 500",
        "^IXIC": "Nasdaq",
        "^DJI": "Dow Jones",
        "^RUT": "Russell 2000"
    }
    
    overview_data = []
    
    try:
        # Fetch data for all tickers at once (efficient)
        tickers = list(indices.keys())
        # period="5d" to ensure we get enough data for previous close calculation even over weekends
        data = yf.download(tickers, period="5d", interval="1d", progress=False, group_by='ticker')
        
        for ticker, name in indices.items():
            try:
                # Access ticker data safely
                ticker_df = data[ticker] if len(tickers) > 1 else data
                
                if ticker_df.empty or len(ticker_df) < 2:
                    continue

                # Get latest two rows (today/latest close, and previous close)
                latest = ticker_df.iloc[-1]
                prev = ticker_df.iloc[-2]
                
                current_price = float(latest['Close'])
                prev_close = float(prev['Close'])
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100
                
                overview_data.append({
                    "name": name,
                    "symbol": ticker,
                    "price": current_price,
                    "change": change,
                    "changePercent": change_percent,
                    "isPositive": change >= 0
                })
            except Exception as inner_e:
                print(f"Error processing {ticker}: {inner_e}")
                continue
                
        return overview_data

    except Exception as e:
        print(f"Error fetching market overview: {e}")
        return []
