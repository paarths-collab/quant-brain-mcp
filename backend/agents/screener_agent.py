from backend.agents.web_agent import WebAgent
from backend.agents.analyst_agent import AnalystAgent
from backend.services.ticker_extractor import TickerExtractor
import asyncio

class ScreenerAgent:

    def __init__(self):
        self.web = WebAgent()
        self.analyst = AnalystAgent()
        self.extractor = TickerExtractor()

    async def discover_stocks(self, query: str):
        # 1. Web Research
        print(f"Searching for stocks based on: {query}")
        research = await asyncio.to_thread(self.web.research, query)

        # 2. Extract Tickers
        articles_text = ""
        if research and "articles" in research:
             articles_text = " ".join([a.get("body", "") for a in research["articles"]])
        
        tickers = self.extractor.extract(articles_text)
        print(f"Found tickers: {tickers}")

        # 3. Analyze Tickers (Limit to Top 5 to save API calls/time)
        ranked = []
        
        # We can't really do async inside a sync method easily without a loop, 
        # but for now we'll do it sequentially or use a helper if we want parallel.
        # User snippet was sequential. Let's keep it simple first.
        
        for t in tickers[:5]:
            try:
                # Basic validation: Check if it looks like a ticker (e.g. not a common word)
                # The Extractor does some of this, but AnalystAgent will fail gracefully if data not found.
                print(f"Analyzing {t}...")
                analysis = self.analyst.analyze(t, market="us") # Defaulting to US for global "AI" search usually
                
                if "error" not in analysis:
                    ranked.append(analysis)
            except Exception as e:
                print(f"Failed to analyze {t}: {e}")

        # 4. Rank by Score
        ranked.sort(key=lambda x: x.get("score", 0), reverse=True)

        return ranked