import yfinance as yf
from typing import Dict, Any

class MacroAgent:
    """Agent for fetching Macroeconomic indicators (Yields, VIX, etc.)"""
    
    def get_global_indicators(self) -> Dict[str, Any]:
        """Fetch key macro indicators"""
        indicators = {}
        tickers = {
            "US_10Y": "^TNX",
            "India_10Y": "^IGSE", # Often not available on free YF, might need proxy
            "VIX": "^VIX",
            "Gold": "GC=F",
            "Oil": "CL=F"
        }
        
        for name, ticker in tickers.items():
            try:
                data = yf.Ticker(ticker)
                info = data.fast_info
                # Check directly last_price or fallback
                price = getattr(info, 'last_price', None)
                if price:
                    indicators[name] = price
                else:
                    # Fallback to history
                    hist = data.history(period="1d")
                    if not hist.empty:
                        indicators[name] = hist['Close'].iloc[-1]
            except Exception as e:
                print(f"⚠️ Macro Fetch Error ({name}): {e}")
                
        return indicators