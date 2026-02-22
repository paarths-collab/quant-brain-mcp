from backend1.core.llm_client import LLMClient
from backend1.agents.web_search_agent import WebSearchAgent
import json
import re

class SentimentAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.web_agent = WebSearchAgent()

    def run(self, ticker: str):
        # 1. Fetch News Summary
        query = f"Recent news sentiment and major headlines for {ticker} stock"
        search_result = self.web_agent.run(query)
        news_summary = search_result.get("summary", "")

        if not news_summary or news_summary == "No result":
             return {"sentiment_score": 0.5, "news_summary": "No recent news found."}

        # 2. Analyze Sentiment with LLM
        prompt = f"""
        Analyze the following news summary for {ticker} and determine the overall sentiment score (0.0 to 1.0).
        0.0 = Extremely Bearish
        0.5 = Neutral
        1.0 = Extremely Bullish
        
        Also extract top 3 key news drivers.

        News Summary:
        {news_summary}

        Respond strictly in JSON:
        {{
            "sentiment_score": 0.0-1.0,
            "drivers": ["driver 1", "driver 2", "driver 3"],
            "summary": "Short 1-sentence summary"
        }}
        """

        try:
            response = self.llm.run_model(
                model="validator", # Use lighter model for extraction
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract JSON
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return data
            else:
                 return {"sentiment_score": 0.5, "news_summary": "Failed to parse sentiment."}

        except Exception as e:
            print(f"Sentiment analysis failed: {e}")
            return {"sentiment_score": 0.5, "error": str(e)}
