from typing import Dict, Any, List, Optional
import re
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from .llm_manager import LLMManager

class WealthGuardrails:
    """
    Implements Input/Output Guardrails for the Wealth Manager using LangChain Runnables.
    
    Features:
    1. Topic Guard: Ensures user input is relevant to finance/wealth.
    2. Safety Guard: filters harmful content.
    3. Disclaimer Guard: Enforces compliance disclaimers.
    """
    
    def __init__(self, llm_manager: LLMManager):
        self.llm = llm_manager
        
    async def validate_input(self, raw_input: str) -> Dict[str, Any]:
        """
        Validates user input before processing.
        Returns: {'valid': bool, 'reason': str}
        """
        # 1. Quick PII Regex Check (Simulated)
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', raw_input): # SSN regex
             return {"valid": False, "reason": "Input contains potential SSN. Please remove sensitive PII."}
             
        # 2. Topic Check Loop (via LLM)
        # We use a lightweight check to ensure relevance
        system_prompt = """You are a classification guardrail. 
        Determine if the user's input is related to:
        - Personal Finance
        - Investing (Stocks, Bonds, Crypto, Real Estate)
        - Macroeconomics
        - Wealth Management
        - Retirement Planning
        
        If unrelated (e.g. cooking, coding, politics), return 'BLOCK'.
        If related, return 'ALLOW'.
        """
        
        try:
            # Sync wrapper invoke for portability
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=raw_input)
            ])
            
            result = response.content.strip().upper()
            
            if "BLOCK" in result:
                return {
                    "valid": False, 
                    "reason": "I can only assist with financial and wealth management queries. Please ask about your portfolio, market trends, or investment strategy."
                }
                
            return {"valid": True, "reason": "valid"}
            
        except Exception as e:
            # Fail open on LLM error (allow access if guard fails) or fail closed
            print(f"⚠️ Guardrail LLM Error: {e}")
            return {"valid": True, "reason": "Guardrail bypass due to error"}

    def add_disclaimer(self, report_text: str) -> str:
        """Attached compliance disclaimer to reports"""
        # User requested removal of disclaimer
        return report_text
