import os
import asyncpraw
from typing import List, Dict

class SentimentAgent:
    """Async Sentiment Analysis Agent using Reddit"""
    
    def __init__(self):
        self.reddit = None
        
    async def _init_reddit(self):
        if not self.reddit:
            self.reddit = asyncpraw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent=os.getenv("REDDIT_USER_AGENT", "wealth_manager_v1")
            )
    
    async def analyze_batch(self, queries: List[str]) -> List[str]:
        """
        Analyze sentiment for a batch of queries (stocks or topics).
        Returns a summary string for each query.
        """
        results = []
        try:
            await self._init_reddit()
            for query in queries:
                # Determine relevant subreddits based on query type roughly
                subreddits = "investing+stocks+finance"
                if "gold" in query.lower(): subreddits = "Gold+Commodities"
                elif "bond" in query.lower(): subreddits = "Bonds+investing"
                elif "mutual fund" in query.lower(): subreddits = "mutualfunds+investing"

                search_query = f"{query}"
                subreddit = await self.reddit.subreddit(subreddits)
                
                titles = []
                scores = []
                async for submission in subreddit.search(search_query, limit=5, sort='relevance', time_filter='month'):
                    titles.append(f"- {submission.title} (Score: {submission.score})")
                    scores.append(submission.score)
                
                if titles:
                    avg_score = sum(scores) / len(scores) if scores else 0
                    summary = f"Reddit Sentiment for '{query}': Active discussion (Avg Score: {avg_score:.0f}).\n" + "\n".join(titles[:3])
                else:
                    summary = f"Reddit Sentiment for '{query}': No significant recent discussions found."
                
                results.append(summary)
                
        except Exception as e:
            print(f"⚠️ Reddit Sentiment Error: {e}")
            results.append(f"Sentiment analysis unavailable for {queries}")
            
        return results

    async def get_ticker_sentiment(self, ticker: str) -> float:
        """Get 0-100 sentiment score for a ticker or topic"""
        try:
            await self._init_reddit()
            score = 0
            count = 0
            # Broader search for topics
            async for post in self.reddit.subreddit("all").search(ticker, time_filter='month', limit=20):
                 # Simple heuristic: heavily upvoted posts imply 'hype' or 'high interest'
                 # We cap individual post impact to avoid skew
                 post_impact = min(post.score, 100) 
                 score += post_impact
                 count += 1
            
            if count == 0: return 50.0
            
            # Normalize: If average score is high, sentiment is "Hot" (100)
            # If low, it's "Cold" (0)
            avg_score = score / count
            # Map 0-50 average score to 0-100 sentiment
            normalized = min((avg_score / 50) * 100, 100)
            
            return round(normalized, 1)

        except Exception as e:
            print(f"⚠️ Ticker Sentiment Error: {e}")
            return 50.0 # Neutral default
            
    async def close(self):
        if self.reddit:
            await self.reddit.close()
