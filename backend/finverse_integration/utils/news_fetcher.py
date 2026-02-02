import os
import requests
import finnhub
from typing import List, Dict, Any

class NewsFetcher:
    """Consolidated News Fetcher for Guardian, Finnhub, and NewsDataIO"""
    
    def __init__(self):
        self.finnhub_client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))
        self.guardian_key = os.getenv("GUARDIAN_API_KEY")
        self.newsdata_key = os.getenv("NEWSDATAIO_API_KEY")

        if not self.guardian_key:
            print("⚠️ Guardian API Key missing")
            
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

    def get_stock_news(self, ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch company news from Finnhub"""
        try:
            # Finnhub Company News
            # Date range: last 1 year usually, simplified here
            news = self.finnhub_client.company_news(ticker, _from="2024-01-01", to="2025-12-31")
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