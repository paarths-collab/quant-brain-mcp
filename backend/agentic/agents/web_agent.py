from duckduckgo_search import DDGS
from backend.agentic.client import LLMClient
import json

class WebAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.ddgs = DDGS()

    async def execute(self, task: str):
        """Execute web research using DuckDuckGo + GPT-OSS"""
        results = []
        try:
            # Safe search
            ddg_results = self.ddgs.text(task, max_results=5)
            if ddg_results:
                results = ddg_results
        except Exception as e:
            return {"error": f"Search failed: {str(e)}", "query": task}

        # Summarize with LLM
        summary = self.llm.run_search_summary(task, results)

        return {
            "search_query": task,
            "results": results,
            "summary": summary
        }
