import ta
import pandas as pd

class MetricsService:

    def compute(self, df):
        if df.empty:
            return {"rsi": 50, "macd": 0} # Default/Neutral
            
        # Ensure Close is float
        df["Close"] = pd.to_numeric(df["Close"], errors='coerce')
        
        # Calculate RSI
        rsi_indicator = ta.momentum.RSIIndicator(df["Close"])
        df["rsi"] = rsi_indicator.rsi()
        
        # Calculate MACD
        macd_indicator = ta.trend.MACD(df["Close"])
        df["macd"] = macd_indicator.macd()

        # Handle NaN values at the beginning of series
        last_rsi = df["rsi"].iloc[-1]
        last_macd = df["macd"].iloc[-1]

        return {
            "rsi": float(last_rsi) if not pd.isna(last_rsi) else 50.0,
            "macd": float(last_macd) if not pd.isna(last_macd) else 0.0
        }
