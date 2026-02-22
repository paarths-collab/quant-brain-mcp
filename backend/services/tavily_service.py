import os
from dotenv import load_dotenv

load_dotenv()

class TavilyService:

    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")
        self.client = None

        try:
            from tavily import TavilyClient  # type: ignore
        except Exception:
            TavilyClient = None  # type: ignore

        if self.api_key and TavilyClient:
            self.client = TavilyClient(api_key=self.api_key)

    def search(self, query):
        if not self.client:
            return []

        try:
            response = self.client.search(query=query, max_results=5)
            return response.get("results", [])
        except Exception as e:
            print(f"Tavily Search failed: {e}")
            return []
