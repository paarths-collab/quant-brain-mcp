
import os
import json
import logging
from typing import Dict, Any, List, Optional
from groq import Groq

logger = logging.getLogger(__name__)

class GroqWebResearcher:
    """
    Advanced Web Researcher using Groq's `groq/compound` model.
    This model has native capabilities for:
    - web_search
    - visit_website
    - code_interpreter
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found. GroqWebResearcher will fail.")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "groq/compound"
        
    def research(self, query: str, include_stock_data: bool = True) -> Dict[str, Any]:
        """
        Perform deep web research using Groq's compound tools.
        """
        logger.info(f"GroqWebResearcher: Researching '{query}'")
        
        try:
            # Define the tools configuration
            # Note: groq/compound specific configuration
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a specialized Web Researcher Agent. Use your tools to find comprehensive, accurate, and up-to-date information."},
                    {"role": "user", "content": f"Research this topic thoroughly: {query}"}
                ],
                temperature=0.7, # Lower temperature for factual research
                max_completion_tokens=1024,
                top_p=1,
                stream=False, # We want the full response for now
                stop=None,
                # compound_custom={"tools":{"enabled_tools":["web_search","code_interpreter","visit_website"]}}
                # Note: The user provided snippet used 'compound_custom' param in the SDK. 
                # Ensuring compatibility with standard SDK if supported, otherwise generic call.
                # Since 'compound_custom' might not be in standard type hints, we pass it as extra_body if needed or kwargs.
                # However, per user snippet:
            )
            
            # Since the user snippet showed specific syntax, we try to match it.
            # But standard OpenAI/Groq client might not accept 'compound_custom' in strict types.
            # We will use the standard valid call, and if 'groq/compound' auto-invokes tools, we parse that.
            # User snippet:
            # completion = client.chat.completions.create(..., compound_custom=...)
            
            # Let's try to pass it via kwargs for the custom param
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a specific Web Research Agent. Find detailed information."},
                    {"role": "user", "content": query}
                ],
                extra_body={
                    "compound_custom": {
                        "tools": {
                            "enabled_tools": ["web_search", "visit_website"]
                        }
                    }
                }
            )
            
            content = response.choices[0].message.content
            
            return {
                "success": True,
                "query": query,
                "web_search": [{"answer": content}],  # Wrapping for compatibility
                "raw_content": content
            }
            
        except Exception as e:
            logger.error(f"GroqWebResearcher failed: {e}")
            return {
                "success": False, 
                "error": str(e),
                "query": query
            }

    def format_for_llm(self, research_data: Dict[str, Any]) -> str:
        """
        Format research data for LLM consumption.
        """
        if not research_data.get("success"):
            return f"Research failed: {research_data.get('error')}"
            
        content = research_data.get("raw_content", "")
        if not content:
             # Fallback to compatibility format
             web_search = research_data.get("web_search", [])
             if web_search:
                 return web_search[0].get("answer", "")
        
        return content

# Factory function replacement
def create_web_researcher(llm_agent=None) -> GroqWebResearcher:
    """Factory function to create the Groq web researcher."""
    return GroqWebResearcher()

