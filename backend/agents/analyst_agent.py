from backend.services.market_data_service import MarketDataService
from backend.services.metrics_service import MetricsService

class AnalystAgent:

    def __init__(self):
        self.data = MarketDataService()
        self.metrics = MetricsService()

    def analyze(self, ticker, market="us"):
        
        # Normalize ticker for the specific market
        ticker = self.data.normalize_ticker(ticker, market)

        try:
            df = self.data.get_history(ticker)
            if df.empty:
                 return {
                    "ticker": ticker,
                    "error": "No historical data found"
                 }
            fundamentals = self.data.get_fundamentals(ticker)
        except Exception as e:
            return {
                "ticker": ticker,
                "error": str(e)
            }

        technicals = self.metrics.compute(df)

        # Best-effort current price for UI/quant headers
        current_price = (
            fundamentals.get("currentPrice")
            or fundamentals.get("regularMarketPrice")
            or fundamentals.get("previousClose")
            or 0
        )

        score = 0
        if technicals["rsi"] < 60:
            score += 30
        
        # Safe access to fundamentals
        trailing_pe = fundamentals.get("trailingPE")
        if trailing_pe and trailing_pe < 40:
            score += 30

        return {
            "ticker": ticker,
            "price": float(current_price) if current_price else 0.0,
            "technicals": technicals,
            "fundamentals": {
                "pe": trailing_pe,
                "market_cap": fundamentals.get("marketCap")
            },
            "score": score
        }
