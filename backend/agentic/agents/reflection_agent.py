from backend.agentic.client import LLMClient
import json

class ReflectionAgent:
    def __init__(self):
        self.llm = LLMClient()

    def review(self, query, agent_outputs, emotional_status, divergence_flags):
        """Review and critique analysis"""
        context = {
            "query": query,
            "outputs": str(agent_outputs)[:4000],
            "emotion": emotional_status,
            "divergence": divergence_flags
        }
        
        messages = [
            {
                "role": "system", 
                "content": "You are a Risk Officer. Check for contradictions, missing risks, or emotional bias. Return JSON."
            },
            {
                "role": "user",
                "content": f"Context: {context}"
            }
        ]
        
        # We invoke LLM but ask for text to avoid parsing issues for now, or use loose parsing
        # For simplicity in this v2 architecture, return text critique to avoid rigid JSON failures in this step
        critique = self.llm.run_reasoning(messages, max_tokens=1000)
        
        return {
            "critique": critique
        }
