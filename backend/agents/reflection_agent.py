
import os
import json
import logging
from typing import Dict, Any, List

from backend.core.llm_client import LLMClient

logger = logging.getLogger(__name__)

class ReflectionAgent:
    """
    Chief Risk Officer / Critic Agent.
    
    Role:
    1. Review the synthesis provided by the Super Agent.
    2. Check for logical fallacies, contradictions, and emotional bias.
    3. Identify missing risks or alternative viewpoints.
    4. Assign a confidence score.
    
    Model: qwen/qwen3-235b-a22b-thinking-2507 (via OpenRouter/LLMClient).
    """
    
    def __init__(self, api_key: str = None):
        # We ignore api_key param as LLMClient handles it via env/config using OPENROUTER_API_KEY
        self.llm = LLMClient()
        # self.model is handled inside LLMClient.deep_reason
        
    def review_plan(self, query: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Critique the initial plan before execution.
        """
        prompt = [
            {"role": "system", "content": "You are a Senior Project Manager reviewing a research plan."},
            {"role": "user", "content": f"""
            User Query: "{query}"
            Proposed Plan: {json.dumps(plan, indent=2)}
            
            Task:
            1. Is this plan efficient?
            2. Does it miss any critical steps (e.g., checking macro context)?
            3. Are the selected tools appropriate?
            
            Return a JSON object:
            {{
                "is_approved": boolean,
                "feedback": "string",
                "suggested_improvements": ["step 1", "step 2"]
            }}
            """}
        ]
        
        try:
            # parsing logic change needed because deep_reason returns an object, not string directly
            response_obj = self.llm.deep_reason(prompt)
            response = response_obj.choices[0].message.content
            
            # Basic cleaning
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1]
                
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Reflection Agent plan review failed: {e}")
            return {"is_approved": True, "feedback": "Review failed, proceeding with original plan.", "suggested_improvements": []}

    def review_synthesis(self, query: str, synthesis: str, execution_log: List[Dict]) -> Dict[str, Any]:
        """
        Critique the final answer before delivery.
        """
        log_summary = json.dumps(execution_log, indent=2)[:5000] # Truncate if too long
        
        prompt = [
            {"role": "system", "content": "You are a Chief Risk Officer reviewing an investment memo."},
            {"role": "user", "content": f"""
            User Query: "{query}"
            
            Draft Response:
            {synthesis}
            
            Evidence (Execution Log):
            {log_summary}
            
            Task:
            1. Are conclusions supported by the evidence?
            2. Are there contradictions between agents (e.g., News vs Financials)?
            3. Is there emotional bias?
            4. What risks are under-discussed?
            
            Return a JSON object:
            {{
                "confidence_score": integer (0-100),
                "critique": "string",
                "missing_risks": ["risk 1", "risk 2"],
                "suggestions_for_improvement": "string"
            }}
            """}
        ]
        
        try:
            response_obj = self.llm.deep_reason(prompt)
            response = response_obj.choices[0].message.content

             # Basic cleaning
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1]
                
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Reflection Agent synthesis review failed: {e}")
            return {
                "confidence_score": 0, 
                "critique": "Review failed.", 
                "missing_risks": [],
                "suggestions_for_improvement": ""
            }
