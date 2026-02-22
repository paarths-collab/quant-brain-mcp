import yfinance as yf

class SectorAgent:

    def analyze(self, etf="SMH", market="us"):
        
        # Adjust sector benchmark based on market
        if market.lower() == "india":
            etf = "^NSEI" # Nifty 50 as proxy for general market/sector health in India context
                          # OR specific sector indices if passed. For now default to Nifty for general 'market' sentiment
                          # if user didn't specify a specific ETF.


        try:
            hist = yf.Ticker(etf).history(period="3mo")
            if hist.empty:
                return {
                    "sector_etf": etf,
                     "error": "No data for ETF"
                }
            
            # Simple momentum calculation
            momentum = hist["Close"].pct_change().mean()

            return {
                "sector_etf": etf,
                "momentum": float(momentum),
                "score": 70 if momentum > 0 else 40
            }
        except Exception as e:
            return {
                "sector_etf": etf,
                "error": str(e)
            }
