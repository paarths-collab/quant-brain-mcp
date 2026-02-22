from backend.services.news_service import NewsService
from backend.agents.sentiment_agent import SentimentAgent

from backend.core.llm_client import LLMClient

class WebAgent:

    def __init__(self):
        self.news = NewsService()
        self.sentiment = SentimentAgent()
        self.llm = LLMClient()

    def research(self, query):

        # 1. Perform raw search (Mechanism)
        # We still need the 'tool' to get data, the LLM 'analyzes' and 'synthesizes' it as requested.
        news_results = self.news.search_news(query)
        
        # 2. LLM Synthesis (The "Web Search Agent" persona)
        # We pass the raw results to the model to "perform" the final answer generation
        context = "\n".join([f"- {r.get('title')}: {r.get('body')}" for r in news_results])
        
        prompt = f"""
        User Query: {query}
        
        Search Results:
        {context}
        
        Task: 
        Analyze the search results above and provide a detailed, in-depth answer to the user's query.
        """
        
        try:
            response = self.llm.web_search_agent(prompt)
            summary = response.choices[0].message.content
        except Exception as e:
            summary = "Error in Web Agent synthesis."
            print(f"WebAgent LLM Error: {e}")

        # 3. Analyze sentiment (keep existing logic or rely on LLM above? Keeping parallel for safety)
        sentiment_data = self.sentiment.analyze(news_results)

        return {
            "articles": news_results,
            "sentiment": sentiment_data["sentiment"],
            "score": sentiment_data["score"],
            "reasoning": summary # Now populated by the LLM
        }
