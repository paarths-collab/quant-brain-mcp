import yfinance as yf
import numpy as np
import pandas as pd

class RegimeDetector:

    def detect(self, ticker):
        try:
            # Fetch data
            df = yf.Ticker(ticker).history(period="6mo")
            if df.empty:
                return {"regime": "Unknown", "volatility": 0.0}

            # Calculate returns and volatility
            returns = df["Close"].pct_change().dropna()
            # Annualized volatility
            volatility = returns.std() * np.sqrt(252)

            # Trend detection (Price > 50 SMA)
            sma_50 = df["Close"].rolling(50).mean().iloc[-1]
            current_price = df["Close"].iloc[-1]
            trend = current_price > sma_50

            # Regime Logic
            if volatility > 0.30: # >30% annualized volatility is high
                regime = "High Volatility"
            elif trend:
                regime = "Bullish Trending"
            else:
                regime = "Sideways / Bearish"

            return {
                "regime": regime,
                "volatility": float(volatility),
                "trend_signal": "Above SMA50" if trend else "Below SMA50"
            }
        except Exception as e:
            print(f"Regime detection error: {e}")
            return {"regime": "Error", "volatility": 0.0}
