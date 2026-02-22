import yfinance as yf

class SectorAgent:
    def __init__(self):
        self.sector_etfs = {
            "technology": "XLK",
            "medical": "XLV", # Medical/Healthcare
            "healthcare": "XLV",
            "finance": "XLF",
            "energy": "XLE",
            "industrial": "XLI",
            "consumer": "XLY", # Discretionary
            "utilities": "XLU",
            "real_estate": "XLRE",
            "materials": "XLB",
            "communication": "XLC"
        }

    async def execute(self, task: str):
        """Analyze sector trends"""
        # Check if task is already a sector key from financial agent
        if task.lower() in self.sector_etfs:
            sector = task.lower()
        else:
            sector = self._detect_sector(task)
            
        encoded_sector = self.sector_etfs.get(sector, "SPY") # Default to market

        try:
            etf = yf.Ticker(encoded_sector)
            hist = etf.history(period="3mo")
            
            if hist.empty:
                 return {"error": "No ETF data"}

            ret_3m = (hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1
            
            return {
                "sector": sector,
                "etf": encoded_sector,
                "performance_3m": f"{ret_3m:.2%}",
                "trend": "bullish" if ret_3m > 0 else "bearish"
            }
        except Exception as e:
            return {"error": str(e)}

    def _detect_sector(self, task: str):
        task_lower = task.lower()
        for s in self.sector_etfs:
            if s in task_lower:
                return s
        return "market" # Fallback
