import os
from dotenv import load_dotenv
from typing import Dict, Any, List
from backend.agents.reddit_search_agent import RedditSearchAgent

load_dotenv()

class SocialService:
    def __init__(self):
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT", "quant-insights-agent")
        
        if client_id and client_secret:
            self.reddit_agent = RedditSearchAgent(client_id, client_secret, user_agent)
        else:
            self.reddit_agent = None
            print("Warning: Reddit credentials missing in .env")

    def get_reddit_posts(self, ticker: str, limit: int = 15) -> Dict[str, Any]:
        """
        Fetches recent Reddit posts for a stock ticker.
        """
        if not self.reddit_agent:
            return {
                "ticker": ticker,
                "error": "Reddit credentials not configured",
                "posts": []
            }
        
        try:
            return self.reddit_agent.search(ticker, limit)
        except Exception as e:
            return {
                "ticker": ticker,
                "error": str(e),
                "posts": []
            }

# Global instance
social_service = SocialService()

def fetch_reddit_posts(ticker: str, limit: int = 15) -> Dict[str, Any]:
    return social_service.get_reddit_posts(ticker, limit)
