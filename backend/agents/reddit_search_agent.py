
"""
reddit_search_agent.py

Fetches Reddit posts related to a given stock ticker.
Pipeline: Ticker → Reddit Search → Posts → Structured Output
"""

from typing import Dict, Any, List
import logging
import re
import praw


class RedditSearchAgent:
    """
    Lightweight Reddit search agent for stock-related posts.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str = "stock-research-agent"
    ):
        """
        Initialize Reddit API client.
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        logging.info("RedditSearchAgent initialized.")

        self.subreddits = [
            "stocks",
            "investing",
            "wallstreetbets",
            "StockMarket"
        ]

    # --------------------------------------------------
    # 🔍 Core Search
    # --------------------------------------------------

    def search(self, ticker: str, limit: int = 25) -> Dict[str, Any]:
        """
        Search Reddit for posts mentioning a ticker.

        Args:
            ticker: Stock ticker symbol (e.g., AAPL)
            limit: Number of posts to fetch

        Returns:
            Structured dictionary of Reddit posts
        """

        query = self._build_query(ticker)
        posts: List[Dict[str, Any]] = []

        for subreddit in self.subreddits:
            try:
                for submission in self.reddit.subreddit(subreddit).search(
                    query=query,
                    sort="new",
                    limit=limit
                ):
                    posts.append({
                        "title": submission.title,
                        "subreddit": subreddit,
                        "score": submission.score,
                        "upvote_ratio": submission.upvote_ratio,
                        "created_utc": submission.created_utc,
                        "url": submission.url,
                        "selftext": submission.selftext[:500],
                        "num_comments": submission.num_comments
                    })
            except Exception as e:
                logging.warning(f"Reddit search failed for r/{subreddit}: {e}")

        return {
            "ticker": ticker.upper(),
            "post_count": len(posts),
            "posts": posts
        }

    # --------------------------------------------------
    # 🧠 Helpers
    # --------------------------------------------------

    @staticmethod
    def _build_query(ticker: str) -> str:
        """
        Build safe Reddit search query.
        """
        ticker = ticker.upper()
        return f'"{ticker}" OR ${ticker}'


# --------------------------------------------------
# 🧪 Standalone Test
# --------------------------------------------------

if __name__ == "__main__":
    agent = RedditSearchAgent(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        user_agent="stock-reddit-agent"
    )

    data = agent.search("AAPL", limit=10)
    print(data)






# social_media_sentiment.py

# Fast AI-powered sentiment analysis using LLM instead of slow Reddit + FinBERT.
# Uses the existing OpenRouter/Gemini API for quick sentiment analysis.
# """

# from typing import Dict, Any


# class SentimentAgent:
#     """
#     Fast sentiment analyzer using LLM API.
#     Replaces slow Reddit scraping + FinBERT with quick AI analysis.
#     """

#     def __init__(self, reddit_client_id: str = None, reddit_client_secret: str = None, 
#                  reddit_user_agent: str = None, llm_agent = None):
#         """
#         Initialize the SentimentAgent.
        
#         Args:
#             reddit_client_id: Deprecated - no longer used
#             reddit_client_secret: Deprecated - no longer used
#             reddit_user_agent: Deprecated - no longer used
#             llm_agent: Optional LLM agent for AI-powered sentiment analysis
#         """
#         self.llm_agent = llm_agent
#         self.initialized = True
#         print("[SUCCESS] SentimentAgent: Initialized (using LLM for fast analysis).")

#     def set_llm_agent(self, llm_agent):
#         """Set the LLM agent for sentiment analysis."""
#         self.llm_agent = llm_agent

#     def analyze(self, ticker: str, company_name: str = None, news_headlines: list = None) -> Dict[str, Any]:
#         """
#         Analyze sentiment for a stock using AI.
        
#         Args:
#             ticker: Stock ticker symbol
#             company_name: Optional company name for context
#             news_headlines: Optional list of news headlines to analyze
            
#         Returns:
#             Dictionary with sentiment analysis results
#         """
#         if not self.llm_agent:
#             # Return a neutral default if no LLM available
#             return {
#                 "Overall Social Sentiment": "Neutral",
#                 "Sentiment Score": 0.5,
#                 "Analysis": "Sentiment analysis unavailable (LLM not configured).",
#                 "Note": "Configure LLM agent for AI-powered sentiment."
#             }

#         try:
#             # Build context for the LLM
#             context = f"Stock: {ticker}"
#             if company_name:
#                 context += f" ({company_name})"
            
#             news_context = ""
#             if news_headlines and len(news_headlines) > 0:
#                 news_context = "\n\nRecent News Headlines:\n" + "\n".join([f"- {h}" for h in news_headlines[:5]])
            
#             prompt = f"""Analyze the market sentiment for {context}.{news_context}

# Based on general market knowledge and any provided news, provide a brief sentiment analysis.

# Respond in this exact JSON format:
# {{
#     "sentiment": "Bullish" or "Bearish" or "Neutral",
#     "confidence": "High" or "Medium" or "Low",
#     "summary": "One sentence summary of sentiment"
# }}

# Only respond with the JSON, nothing else."""

#             # Call the LLM
#             response = self.llm_agent.run(
#                 prompt=prompt,
#                 model_name="xiaomi/mimo-v2-flash:free"
#             )
            
#             # Parse the response
#             import json
#             try:
#                 # Try to extract JSON from response
#                 response_clean = response.strip()
#                 if response_clean.startswith("```"):
#                     # Remove markdown code blocks
#                     response_clean = response_clean.split("```")[1]
#                     if response_clean.startswith("json"):
#                         response_clean = response_clean[4:]
                
#                 result = json.loads(response_clean)
                
#                 return {
#                     "Overall Social Sentiment": result.get("sentiment", "Neutral"),
#                     "Confidence": result.get("confidence", "Medium"),
#                     "Analysis": result.get("summary", "Sentiment analyzed via AI."),
#                     "Method": "AI Analysis (Fast)"
#                 }
#             except json.JSONDecodeError:
#                 # If JSON parsing fails, extract sentiment from text
#                 response_lower = response.lower()
#                 if "bullish" in response_lower:
#                     sentiment = "Bullish"
#                 elif "bearish" in response_lower:
#                     sentiment = "Bearish"
#                 else:
#                     sentiment = "Neutral"
                
#                 return {
#                     "Overall Social Sentiment": sentiment,
#                     "Analysis": response[:200] if len(response) > 200 else response,
#                     "Method": "AI Analysis (Fast)"
#                 }
                
#         except Exception as e:
#             print(f"[WARNING] SentimentAgent: AI analysis failed: {e}")
#             return {
#                 "Overall Social Sentiment": "Neutral",
#                 "Analysis": f"Sentiment analysis skipped: {str(e)[:50]}",
#                 "Method": "Fallback"
#             }


# # For backwards compatibility - quick test
# if __name__ == "__main__":
#     agent = SentimentAgent()
#     print(agent.analyze("AAPL", "Apple Inc."))