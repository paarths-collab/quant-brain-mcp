"""
Tools package for LangChain/AutoGen integration.
"""

from .duckduckgo_mcp import (
    DuckDuckGoMCPTool,
    get_search_tool,
    get_langchain_tool,
    LANGCHAIN_TOOL_AVAILABLE,
)

__all__ = [
    "DuckDuckGoMCPTool",
    "get_search_tool",
    "get_langchain_tool",
    "LANGCHAIN_TOOL_AVAILABLE",
]
