"""
Multi-Source Data Scraper for Emotion Context
Gathers news, social sentiment, market events, and volatility data
to provide comprehensive emotional context for trading decisions.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import os

import pandas as pd
import requests
from bs4 import BeautifulSoup

from backend.utils.sentiment import analyze_text_sentiment, calculate_headline_sentiment

try:
    from backend.finverse_integration.utils.news_fetcher import NewsFetcher
except Exception:
    NewsFetcher = None


class EmotionDataScraper:
    """
    Comprehensive scraper for emotional trading context.
    Sources: News, Reddit, Market Events, Options Flow
    """
    
    def __init__(self):
        self.news_fetcher = NewsFetcher() if NewsFetcher else None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_all(self, ticker: str, market: str = "us") -> Dict[str, Any]:
        """
        Main entry point: scrape all emotional context sources
        """
        return {
            "ticker": ticker,
            "timestamp": datetime.utcnow().isoformat(),
            "news": self.scrape_news(ticker),
            "social_sentiment": self.scrape_social_sentiment(ticker),
            "market_events": self.scrape_market_events(ticker),
            "options_sentiment": self.scrape_options_sentiment(ticker),
            "insider_activity": self.scrape_insider_activity(ticker),
            "analyst_actions": self.scrape_analyst_actions(ticker),
        }
    
    def scrape_news(self, ticker: str, days_back: int = 7) -> Dict[str, Any]:
        """
        Scrape recent news headlines and compute sentiment
        """
        headlines = []
        
        # Try NewsFetcher first
        if self.news_fetcher:
            try:
                news_data = self.news_fetcher.fetch_news(ticker, limit=20)
                if news_data and isinstance(news_data, list):
                    for item in news_data:
                        if isinstance(item, dict):
                            headlines.append({
                                "title": item.get("title", ""),
                                "source": item.get("source", "API"),
                                "published": item.get("published_date", ""),
                                "url": item.get("url", ""),
                            })
            except Exception as e:
                print(f"NewsFetcher error: {e}")
        
        # Fallback: Yahoo Finance news scraping
        if len(headlines) < 5:
            headlines.extend(self._scrape_yahoo_news(ticker))
        
        # Compute sentiment for each headline
        for headline in headlines:
            sentiment_result = analyze_text_sentiment(headline.get("title", ""))
            headline["sentiment_score"] = sentiment_result.get("score", 0)
            headline["sentiment_label"] = sentiment_result.get("label", "neutral")
        
        # Aggregate statistics
        sentiments = [h.get("sentiment_score", 0) for h in headlines if h.get("sentiment_score") is not None]
        
        return {
            "available": len(headlines) > 0,
            "count": len(headlines),
            "headlines": headlines[:10],  # Return top 10
            "avg_sentiment": sum(sentiments) / len(sentiments) if sentiments else 0,
            "negative_count": sum(1 for s in sentiments if s < -0.1),
            "positive_count": sum(1 for s in sentiments if s > 0.1),
            "neutral_count": sum(1 for s in sentiments if -0.1 <= s <= 0.1),
        }
    
    def scrape_social_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        Scrape Reddit (WSB, stocks, investing) for social sentiment
        """
        mentions = []
        sentiment_scores = []
        
        # Scrape Reddit (using public API - no auth needed for reading)
        subreddits = ["wallstreetbets", "stocks", "investing"]
        
        for subreddit in subreddits:
            try:
                mentions_data = self._scrape_reddit_mentions(ticker, subreddit)
                mentions.extend(mentions_data)
                sentiment_scores.extend([m.get("sentiment", 0) for m in mentions_data])
            except Exception as e:
                print(f"Reddit scrape error ({subreddit}): {e}")
        
        # Compute aggregate
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        return {
            "available": len(mentions) > 0,
            "total_mentions": len(mentions),
            "avg_sentiment": round(avg_sentiment, 3),
            "mentions": mentions[:5],  # Top 5
            "emotion_keywords": self._extract_emotion_keywords(mentions),
        }
    
    def scrape_market_events(self, ticker: str) -> Dict[str, Any]:
        """
        Scrape upcoming earnings, dividends, splits
        """
        events = []
        
        try:
            # Use Yahoo Finance or similar
            events = self._scrape_yahoo_events(ticker)
        except Exception as e:
            print(f"Market events scrape error: {e}")
        
        return {
            "available": len(events) > 0,
            "upcoming_events": events,
            "has_earnings_soon": any(e.get("type") == "earnings" for e in events),
        }
    
    def scrape_options_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        Scrape options flow data (put/call ratio, unusual activity)
        """
        try:
            # This would typically use a paid API like Unusual Whales or CBOE
            # For now, return structure with placeholder
            return {
                "available": False,
                "reason": "Options API not configured",
                "put_call_ratio": None,
                "unusual_activity": [],
            }
        except Exception as e:
            return {
                "available": False,
                "reason": str(e),
            }
    
    def scrape_insider_activity(self, ticker: str, days_back: int = 90) -> Dict[str, Any]:
        """
        Scrape recent insider buying/selling
        """
        insider_trades = []
        
        try:
            # Scrape from SEC or finviz
            insider_trades = self._scrape_finviz_insider(ticker)
        except Exception as e:
            print(f"Insider scrape error: {e}")
        
        buys = [t for t in insider_trades if t.get("transaction") == "buy"]
        sells = [t for t in insider_trades if t.get("transaction") == "sell"]
        
        return {
            "available": len(insider_trades) > 0,
            "total_trades": len(insider_trades),
            "buys": len(buys),
            "sells": len(sells),
            "recent_trades": insider_trades[:5],
            "net_signal": "bullish" if len(buys) > len(sells) else "bearish" if len(sells) > len(buys) else "neutral",
        }
    
    def scrape_analyst_actions(self, ticker: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Scrape recent analyst upgrades/downgrades
        """
        actions = []
        
        try:
            actions = self._scrape_analyst_ratings(ticker)
        except Exception as e:
            print(f"Analyst scrape error: {e}")
        
        upgrades = [a for a in actions if a.get("action") == "upgrade"]
        downgrades = [a for a in actions if a.get("action") == "downgrade"]
        
        return {
            "available": len(actions) > 0,
            "total_actions": len(actions),
            "upgrades": len(upgrades),
            "downgrades": len(downgrades),
            "recent_actions": actions[:5],
            "net_signal": "bullish" if len(upgrades) > len(downgrades) else "bearish" if len(downgrades) > len(upgrades) else "neutral",
        }
    
    # ===== PRIVATE HELPER METHODS =====
    
    def _scrape_yahoo_news(self, ticker: str) -> List[Dict[str, Any]]:
        """Scrape Yahoo Finance news"""
        headlines = []
        
        try:
            url = f"https://finance.yahoo.com/quote/{ticker}/news"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find news articles (Yahoo's structure)
                articles = soup.find_all('h3', limit=10)
                
                for article in articles:
                    link = article.find('a')
                    if link:
                        headlines.append({
                            "title": link.get_text(strip=True),
                            "source": "Yahoo Finance",
                            "published": "",
                            "url": link.get('href', ''),
                        })
        except Exception as e:
            print(f"Yahoo news scrape error: {e}")
        
        return headlines
    
    def _scrape_reddit_mentions(self, ticker: str, subreddit: str) -> List[Dict[str, Any]]:
        """Scrape Reddit mentions using public JSON API"""
        mentions = []
        
        try:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {
                "q": f"${ticker} OR {ticker}",
                "restrict_sr": "1",
                "sort": "new",
                "limit": 25,
                "t": "week",
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get("data", {}).get("children", [])
                
                for post in posts:
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    
                    # Simple sentiment from title
                    sentiment_result = analyze_text_sentiment(title)
                    
                    mentions.append({
                        "text": title,
                        "subreddit": subreddit,
                        "score": post_data.get("score", 0),
                        "created_utc": post_data.get("created_utc", 0),
                        "sentiment": sentiment_result.get("score", 0),
                    })
        except Exception as e:
            print(f"Reddit API error: {e}")
        
        return mentions
    
    def _scrape_yahoo_events(self, ticker: str) -> List[Dict[str, Any]]:
        """Scrape upcoming events from Yahoo Finance"""
        events = []
        
        try:
            # This would typically scrape the calendar section
            # Placeholder for now
            pass
        except Exception as e:
            print(f"Events scrape error: {e}")
        
        return events
    
    def _scrape_finviz_insider(self, ticker: str) -> List[Dict[str, Any]]:
        """Scrape insider trading from Finviz"""
        trades = []
        
        try:
            url = f"https://finviz.com/quote.ashx?t={ticker}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find insider trading table
                tables = soup.find_all('table', class_='body-table')
                
                for table in tables:
                    rows = table.find_all('tr')[1:]  # Skip header
                    
                    for row in rows[:5]:  # Top 5
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            trades.append({
                                "insider": cols[0].get_text(strip=True),
                                "relationship": cols[1].get_text(strip=True),
                                "date": cols[2].get_text(strip=True),
                                "transaction": "buy" if "buy" in cols[3].get_text(strip=True).lower() else "sell",
                                "shares": cols[4].get_text(strip=True) if len(cols) > 4 else "",
                            })
        except Exception as e:
            print(f"Finviz scrape error: {e}")
        
        return trades
    
    def _scrape_analyst_ratings(self, ticker: str) -> List[Dict[str, Any]]:
        """Scrape analyst ratings/upgrades/downgrades"""
        actions = []
        
        try:
            # Would scrape from Benzinga, MarketWatch, or similar
            # Placeholder for now
            pass
        except Exception as e:
            print(f"Analyst ratings scrape error: {e}")
        
        return actions
    
    def _extract_emotion_keywords(self, mentions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract emotional keywords from social mentions"""
        emotion_words = {
            "bullish": 0,
            "bearish": 0,
            "moon": 0,
            "crash": 0,
            "buy": 0,
            "sell": 0,
            "hold": 0,
            "panic": 0,
            "fomo": 0,
            "dip": 0,
        }
        
        for mention in mentions:
            text = mention.get("text", "").lower()
            for word in emotion_words:
                if word in text:
                    emotion_words[word] += 1
        
        return emotion_words


# Singleton instance
_SCRAPER = None


def get_scraper() -> EmotionDataScraper:
    """Get or create singleton scraper instance"""
    global _SCRAPER
    if _SCRAPER is None:
        _SCRAPER = EmotionDataScraper()
    return _SCRAPER


def scrape_emotion_data(ticker: str, market: str = "us") -> Dict[str, Any]:
    """
    Convenience function to scrape all emotion data for a ticker
    """
    scraper = get_scraper()
    return scraper.scrape_all(ticker, market)
