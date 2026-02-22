import numpy as np
import yfinance as yf

class RiskModels:

    def calculate_var(self, ticker, confidence=0.95):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            if df.empty: return 0.0
            returns = df["Close"].pct_change().dropna()
            
            # Historical VaR
            # The return at the (1-confidence) percentile
            var = np.percentile(returns, (1 - confidence) * 100)
            return float(var)
        except Exception:
            return 0.0

    def calculate_cvar(self, ticker, confidence=0.95):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            if df.empty: return 0.0
            returns = df["Close"].pct_change().dropna()

            var_threshold = np.percentile(returns, (1 - confidence) * 100)
            # Average of returns worse than VaR
            cvar = returns[returns <= var_threshold].mean()
            return float(cvar) if not np.isnan(cvar) else 0.0
        except Exception:
            return 0.0

    def max_drawdown(self, ticker):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            if df.empty: return 0.0
            # Cumulative return index
            cumulative = (1 + df["Close"].pct_change().dropna()).cumprod()
            peak = cumulative.cummax()
            drawdown = (cumulative - peak) / peak
            return float(drawdown.min())
        except Exception:
            return 0.0
