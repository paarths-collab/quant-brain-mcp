import yfinance as yf
import pandas as pd
import numpy as np

class TechnicalAnalystAgent:

    def run(self, ticker: str):
        ticker = ticker.strip().upper()
        if not ticker: return {}

        try:
            stock = yf.Ticker(ticker)
            # Fetch 1y to compute SMA200, but compute indicators on daily
            hist = stock.history(period="1y")

            if hist.empty or len(hist) < 200:
                # Fallback slightly shorter if new IPO
                if len(hist) < 50:
                    return {"error": "Insufficient history"}
            
            close = hist["Close"]
            
            # 1. RSI (14)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # 2. MACD (12, 26, 9)
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            
            macd_val = macd.iloc[-1]
            signal_val = signal.iloc[-1]
            
            # 3. SMA / Trend
            sma50 = close.rolling(window=50).mean().iloc[-1]
            sma200 = close.rolling(window=200).mean().iloc[-1] if len(close) >= 200 else None
            
            current_price = close.iloc[-1]
            
            trend = "Neutral"
            if item := (current_price > sma50):
                 if sma50 > (sma200 or 0):
                      trend = "Bullish"
                 else:
                      trend = "Recovering" # Price > 50 but 50 < 200
            elif current_price < sma50:
                 if sma50 < (sma200 or 999999):
                      trend = "Bearish"

            # 4. Volatility (Annualized)
            daily_returns = close.pct_change()
            volatility = daily_returns.std() * np.sqrt(252)

            return {
                "rsi": float(current_rsi),
                "macd": float(macd_val),
                "macd_signal": "Bullish" if macd_val > signal_val else "Bearish",
                "trend": trend,
                "sma50": float(sma50),
                "sma200": float(sma200) if sma200 else None,
                "price": float(current_price),
                "volatility": float(volatility)
            }

        except Exception as e:
            print(f"Technical analysis error for {ticker}: {e}")
            return {"error": str(e)}
