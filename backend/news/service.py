from .core.duckduckgo_service import DuckDuckGoService
from .core.gnews_service import GNewsService
from .core.tavily_service import TavilyService
import re
class NewsService:

    def __init__(self):
        self.gnews = GNewsService()
        self.ddg = DuckDuckGoService()
        self.tavily = TavilyService()

    def _optimize_news_query(self, query: str) -> str:
        q = (query or "").strip()
        if not q:
            return ""

        # If user message contains a clear ticker, focus the news query on it.
        candidates = re.findall(r"\b[A-Z]{1,5}(?:\.[A-Z]{2})?\b", q)
        blacklist = {"AI", "US", "USA", "UK", "EU", "GDP", "ETF", "IPO", "AND", "THE", "FOR", "TO", "OF"}
        tickers = [c for c in candidates if c not in blacklist]
        if tickers:
            t = tickers[0]
            if not re.search(r"\bnews\b|\bheadlines?\b", q, flags=re.IGNORECASE):
                return f"{t} stock news"
            return q

        # Otherwise, gently bias towards news queries if needed.
        if re.search(r"\bnews\b|\bheadlines?\b", q, flags=re.IGNORECASE):
            return q
        return f"{q} news"

    def search_news(self, query):
        query = self._optimize_news_query(query)
        if not query:
            return []

        # Prefer GNews (purpose-built for news)
        results = self.gnews.search(query)

        # Fallback to DDG
        if not results:
            results = self.ddg.search(query)

        # If DDG fails or empty → fallback to Tavily
        if not results:
            print(f"No results for '{query}', falling back to Tavily.")
            results = self.tavily.search(query)

        # Normalize fields for downstream consumers (title/body/href)
        normalized = []
        for r in results or []:
            if not isinstance(r, dict):
                continue
            normalized.append({
                "title": r.get("title") or r.get("name") or "",
                "href": r.get("href") or r.get("url") or "",
                "body": r.get("body") or r.get("content") or r.get("snippet") or r.get("description") or "",
            })

        return normalized
