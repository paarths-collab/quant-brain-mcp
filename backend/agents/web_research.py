"""
web_research.py

Web research module using Tavily for search and FireCrawl for web scraping.
Provides AI-powered research capabilities for the Research Agent.

Flow:
1. Analyze user query with AI to understand intent
2. Search web using Tavily for relevant information
3. Optionally scrape specific URLs with FireCrawl
4. Combine with stock data and send to AI for synthesis
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional


# API Keys (can be overridden from config)
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "fc-f93babf1646d41bebd62aa52b9b43109")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")


class TavilySearch:
    """
    Tavily Search API wrapper for AI-powered web search.
    """
    
    BASE_URL = "https://api.tavily.com/search"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or TAVILY_API_KEY
    
    def search(self, query: str, max_results: int = 5, search_depth: str = "basic") -> Dict[str, Any]:
        """
        Search the web using Tavily.
        
        Args:
            query: Search query
            max_results: Maximum number of results (1-10)
            search_depth: 'basic' or 'advanced'
            
        Returns:
            Dictionary with search results
        """
        try:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": min(max_results, 10),
                "search_depth": search_depth,
                "include_answer": True,
                "include_raw_content": False
            }
            
            response = requests.post(self.BASE_URL, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "success": True,
                "query": query,
                "answer": data.get("answer", ""),
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", "")[:500],  # Limit content length
                        "score": r.get("score", 0)
                    }
                    for r in data.get("results", [])
                ]
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Tavily search failed: {str(e)}",
                "query": query,
                "results": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "query": query,
                "results": []
            }


class FireCrawlScraper:
    """
    FireCrawl API wrapper for web scraping.
    """
    
    BASE_URL = "https://api.firecrawl.dev/v1"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or FIRECRAWL_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def scrape(self, url: str, formats: List[str] = None) -> Dict[str, Any]:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            formats: Output formats ('markdown', 'html', 'text')
            
        Returns:
            Dictionary with scraped content
        """
        if formats is None:
            formats = ["markdown"]
        
        try:
            payload = {
                "url": url,
                "formats": formats
            }
            
            response = requests.post(
                f"{self.BASE_URL}/scrape",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("success"):
                content = data.get("data", {})
                return {
                    "success": True,
                    "url": url,
                    "title": content.get("metadata", {}).get("title", ""),
                    "markdown": content.get("markdown", "")[:3000],  # Limit content
                    "metadata": content.get("metadata", {})
                }
            else:
                return {
                    "success": False,
                    "url": url,
                    "error": data.get("error", "Unknown error")
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "url": url,
                "error": f"FireCrawl scrape failed: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": f"Unexpected error: {str(e)}"
            }


class WebResearcher:
    """
    AI-powered web research combining Tavily search and FireCrawl scraping.
    
    Flow:
    1. AI analyzes query to understand intent
    2. Searches web with Tavily
    3. Optionally scrapes specific URLs
    4. Returns combined research data
    """
    
    def __init__(self, llm_agent=None, tavily_key: str = None, firecrawl_key: str = None):
        self.llm = llm_agent
        self.tavily = TavilySearch(api_key=tavily_key)
        self.firecrawl = FireCrawlScraper(api_key=firecrawl_key)
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Use AI to analyze the query and determine research strategy.
        
        Args:
            query: User's research question
            
        Returns:
            Analysis with search queries and strategy
        """
        if not self.llm:
            # Fallback without AI
            return {
                "search_queries": [query],
                "needs_scraping": False,
                "intent": "general_research"
            }
        
        analysis_prompt = f"""Analyze this research question and respond with ONLY valid JSON:

User Question: "{query}"

Determine:
1. What search queries would help answer this question? (generate 1-3 targeted queries)
2. Does this need deep web scraping or just search results?
3. What is the user's intent?

Respond in this format only:
{{"search_queries": ["query1", "query2"], "needs_scraping": false, "intent": "financial_research|news|company_info|general"}}"""

        try:
            response = self.llm.run(prompt=analysis_prompt, model_name="xiaomi/mimo-v2-flash:free")
            
            # Clean up response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            response = response.strip()
            
            return json.loads(response)
        except Exception as e:
            print(f"Query analysis failed: {e}")
            return {
                "search_queries": [query],
                "needs_scraping": False,
                "intent": "general_research"
            }
    
    def research(self, query: str, include_stock_data: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive web research.
        
        Args:
            query: User's research question
            include_stock_data: Whether to also gather stock data
            
        Returns:
            Research results with web data and optional stock analysis
        """
        results = {
            "query": query,
            "web_search": [],
            "scraped_content": [],
            "stock_data": None,
            "success": True
        }
        
        # Step 1: Analyze query with AI
        analysis = self.analyze_query(query)
        search_queries = analysis.get("search_queries", [query])
        needs_scraping = analysis.get("needs_scraping", False)
        
        # Step 2: Search web with Tavily
        for search_query in search_queries[:2]:  # Limit to 2 searches
            search_result = self.tavily.search(search_query, max_results=3)
            if search_result.get("success"):
                results["web_search"].append({
                    "query": search_query,
                    "answer": search_result.get("answer", ""),
                    "sources": search_result.get("results", [])
                })
        
        # Step 3: Optionally scrape top URLs for more detail
        if needs_scraping and results["web_search"]:
            urls_to_scrape = []
            for search in results["web_search"]:
                for source in search.get("sources", [])[:1]:  # Top 1 from each search
                    if source.get("url"):
                        urls_to_scrape.append(source["url"])
            
            for url in urls_to_scrape[:2]:  # Limit to 2 scrapes
                scrape_result = self.firecrawl.scrape(url)
                if scrape_result.get("success"):
                    results["scraped_content"].append({
                        "url": url,
                        "title": scrape_result.get("title", ""),
                        "content": scrape_result.get("markdown", "")[:2000]
                    })
        
        return results
    
    def format_for_llm(self, research_data: Dict[str, Any]) -> str:
        """
        Format research data for LLM consumption.
        
        Args:
            research_data: Research results from research() method
            
        Returns:
            Formatted string for LLM context
        """
        parts = []
        
        # Web search results
        if research_data.get("web_search"):
            parts.append("## Web Search Results\n")
            for search in research_data["web_search"]:
                if search.get("answer"):
                    parts.append(f"**Quick Answer:** {search['answer']}\n")
                
                for source in search.get("sources", []):
                    parts.append(f"### {source.get('title', 'Untitled')}")
                    parts.append(f"Source: {source.get('url', 'N/A')}")
                    parts.append(f"{source.get('content', '')}\n")
        
        # Scraped content
        if research_data.get("scraped_content"):
            parts.append("\n## Detailed Content\n")
            for item in research_data["scraped_content"]:
                parts.append(f"### {item.get('title', 'Untitled')}")
                parts.append(f"Source: {item.get('url', 'N/A')}")
                parts.append(f"{item.get('content', '')[:1500]}\n")
        
        return "\n".join(parts) if parts else "No web research data available."


def create_web_researcher(llm_agent=None) -> WebResearcher:
    """Factory function to create a web researcher."""
    return WebResearcher(llm_agent=llm_agent)
