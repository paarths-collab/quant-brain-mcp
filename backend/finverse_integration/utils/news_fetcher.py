import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests
import finnhub
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("⚠️ duckduckgo-search not installed")

class NewsFetcher:
    """Consolidated News Fetcher for Guardian, Finnhub, and NewsDataIO"""
    
    def __init__(self):
        self.finnhub_client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))
        self.guardian_key = os.getenv("GUARDIAN_API_KEY")
        self.newsdata_key = os.getenv("NEWSDATAIO_API_KEY")

        if not self.guardian_key:
            print("⚠️ Guardian API Key missing")
            
    def fetch_news(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Unified news fetcher (Finnhub -> DuckDuckGo fallback)
        Matches the signature expected by EmotionDataScraper
        """
        # Try primary API (Finnhub)
        news = self.get_stock_news(ticker, limit=limit)
        if news:
            return news
            
        # Fallback to DuckDuckGo
        if DDGS_AVAILABLE:
            try:
                print(f"🦆 Fetching news for {ticker} from DuckDuckGo...")
                with DDGS() as ddgs:
                    results = list(ddgs.news(keywords=f"{ticker} stock news", max_results=limit))
                    formatted = []
                    for r in results:
                        formatted.append({
                            "title": r.get('title', ''),
                            "url": r.get('url', ''),
                            "source": r.get('source', 'DuckDuckGo'),
                            "published_date": r.get('date', ''),
                            "summary": r.get('body', '')
                        })
                    return formatted
            except Exception as e:
                print(f"⚠️ DuckDuckGo News Error: {e}")
        
        return []

    def get_sector_news(self, sector: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch news for a specific sector from Guardian"""
        url = "https://content.guardianapis.com/search"
        params = {
            "api-key": self.guardian_key,
            "section": "business",
            "q": f"{sector} OR market OR economy",
            "order-by": "newest",
            "page-size": limit
        }
        try:
            response = requests.get(url, params=params)
            data = response.json()
            results = data.get('response', {}).get('results', [])
            return [{"title": r['webTitle'], "url": r['webUrl'], "source": "Guardian"} for r in results]
        except Exception as e:
            print(f"⚠️ Guardian News Error: {e}")
            return []

    def get_stock_news(
        self,
        ticker: str,
        limit: int = 5,
        days_back: int = 90
    ) -> List[Dict[str, Any]]:
        """Fetch company news from Finnhub"""
        try:
            # Finnhub Company News (recent window)
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=max(1, days_back))

            news = self.finnhub_client.company_news(
                ticker,
                _from=start_date.isoformat(),
                to=end_date.isoformat()
            )
            formatted = []
            for n in news[:limit]:
                formatted.append({
                    "title": n['headline'],
                    "summary": n['summary'],
                    "source": n['source'],
                    "url": n['url']
                })
            return formatted
        except Exception as e:
            print(f"⚠️ Finnhub Stock News Error: {e}")
            return []

    def get_category_news(self, category_query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch news for generic categories (e.g. Mutual Funds) using NewsDataIO"""
        if not self.newsdata_key:
            return []
            
        url = "https://newsdata.io/api/1/news"
        params = {
            "apikey": self.newsdata_key,
            "q": category_query,
            "language": "en"
        }
        try:
            r = requests.get(url, params=params)
            data = r.json()
            return [{"title": a['title'], "source": "NewsDataIO"} for a in data.get('results', [])[:limit]]
        except Exception as e:
            print(f"⚠️ NewsDataIO Error: {e}")
            return []
