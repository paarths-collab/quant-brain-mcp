"""
DuckDuckGo MCP Tool for LangChain integration.
Provides web and news search capabilities for financial research.
"""

import os
from typing import Dict, Any, List, Optional

# Try docker-based MCP first, fallback to direct library
DOCKER_MCP_URL = os.getenv("DUCKDUCKGO_MCP_URL", "http://localhost:8020")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False


class DuckDuckGoMCPTool:
    """
    DuckDuckGo search tool that works with:
    1. Docker MCP server (if running)
    2. Direct duckduckgo_search library (fallback)
    
    Use this for stock research, news, sentiment analysis.
    """
    
    name = "stock_web_research"
    description = (
        "Use this tool to research stocks, companies, market news, "
        "financial performance, and recent events from the web. "
        "Returns relevant search results with titles, snippets, and sources."
    )
    
    def __init__(self, use_mcp: bool = False, mcp_url: str = None):
        """
        Args:
            use_mcp: Try Docker MCP server first
            mcp_url: Custom MCP server URL
        """
        self.use_mcp = use_mcp
        self.mcp_url = mcp_url or DOCKER_MCP_URL
    
    def _run(self, query: str, num_results: int = 8) -> str:
        """Execute search and return formatted results."""
        return self.search(query, num_results)
    
    def search(self, query: str, num_results: int = 8) -> str:
        """
        Search the web for information.
        
        Args:
            query: Search query (e.g., "AAPL stock news earnings")
            num_results: Number of results to return
            
        Returns:
            Formatted string of search results
        """
        # Try MCP server first if enabled
        if self.use_mcp and REQUESTS_AVAILABLE:
            try:
                results = self._search_via_mcp(query, num_results)
                if results:
                    return results
            except Exception as e:
                print(f"MCP search failed, falling back to direct: {e}")
        
        # Direct library search
        if DDGS_AVAILABLE:
            return self._search_direct(query, num_results)
        
        return "Error: No search method available. Install duckduckgo_search or start MCP server."
    
    def news(self, query: str, num_results: int = 8) -> str:
        """
        Search for news articles.
        
        Args:
            query: News query (e.g., "TSLA stock")
            num_results: Number of results
            
        Returns:
            Formatted news results
        """
        if DDGS_AVAILABLE:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.news(keywords=query, max_results=num_results))
                    return self._format_news_results(results)
            except Exception as e:
                return f"News search error: {e}"
        
        # Fallback to regular search with news keywords
        return self.search(f"{query} news latest", num_results)
    
    def _search_via_mcp(self, query: str, num_results: int) -> Optional[str]:
        """Search using Docker MCP server."""
        response = requests.post(
            f"{self.mcp_url}/mcp",
            json={
                "tool": "web-search",
                "query": query,
                "numResults": num_results
            },
            timeout=30
        )
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        return self._format_results(data.get("results", []))
    
    def _search_direct(self, query: str, num_results: int) -> str:
        """Search using duckduckgo_search library directly."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(keywords=query, max_results=num_results))
                return self._format_results([
                    {
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", "")
                    }
                    for r in results
                ])
        except Exception as e:
            return f"Search error: {e}"
    
    def _format_results(self, results: List[Dict]) -> str:
        """Format search results as readable text."""
        if not results:
            return "No results found."
        
        formatted = []
        for i, item in enumerate(results, 1):
            formatted.append(
                f"{i}. {item.get('title', 'No title')}\n"
                f"   {item.get('snippet', '')}\n"
                f"   Source: {item.get('url', 'N/A')}"
            )
        
        return "\n\n".join(formatted)
    
    def _format_news_results(self, results: List[Dict]) -> str:
        """Format news results."""
        if not results:
            return "No news found."
        
        formatted = []
        for i, item in enumerate(results, 1):
            formatted.append(
                f"{i}. {item.get('title', 'No title')}\n"
                f"   {item.get('body', '')[:200]}...\n"
                f"   Source: {item.get('source', 'Unknown')} | {item.get('date', '')}"
            )
        
        return "\n\n".join(formatted)


# LangChain compatibility
try:
    from langchain.tools import BaseTool
    
    class DuckDuckGoSearchTool(BaseTool):
        """LangChain-compatible DuckDuckGo search tool."""
        
        name: str = "stock_web_research"
        description: str = (
            "Use this tool to research stocks, companies, market news, "
            "financial performance, and recent events from the web."
        )
        
        def _run(self, query: str) -> str:
            tool = DuckDuckGoMCPTool()
            return tool.search(query)
        
        async def _arun(self, query: str) -> str:
            return self._run(query)
    
    LANGCHAIN_TOOL_AVAILABLE = True
    
except ImportError:
    LANGCHAIN_TOOL_AVAILABLE = False
    DuckDuckGoSearchTool = None


def get_search_tool():
    """Get the appropriate search tool instance."""
    return DuckDuckGoMCPTool()


def get_langchain_tool():
    """Get LangChain-compatible tool if available."""
    if LANGCHAIN_TOOL_AVAILABLE:
        return DuckDuckGoSearchTool()
    return None
