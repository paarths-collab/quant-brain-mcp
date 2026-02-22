import yfinance as yf
import numpy as np


class RiskAgent:

    def run(self, task: str, state=None):
        # 1. Try to get ticker from financial state first (most reliable)
        ticker = None
        if state and "financial" in state and "ticker" in state["financial"]:
            ticker = state["financial"]["ticker"]
        
        # 2. Fallback to extracting from task string if state is missing
        if not ticker:
            ticker = self._extract_ticker(task)

        if not ticker:
            return {"error": "No ticker found in state or task"}

        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist.empty:
            return {"error": "No historical data"}

        returns = hist["Close"].pct_change().dropna()

        volatility = np.std(returns) * np.sqrt(252)
        var_95 = np.percentile(returns, 5)

        return {
            "volatility_annual": float(volatility),
            "VaR_95_daily": float(var_95)
        }

    def _extract_ticker(self, text):
        words = text.split()
        for w in words:
            if w.isupper() and len(w) <= 5:
                return w
        return None
