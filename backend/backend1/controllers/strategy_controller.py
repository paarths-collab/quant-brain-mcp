from backend1.core.llm_client import LLMClient
from backend1.controllers.controller_prompt import CONTROLLER_SYSTEM_PROMPT


class StrategyController:

    def __init__(self):
        self.llm = LLMClient()

    def detect_market(self, user_input: str):
        if ".NS" in user_input or ".BO" in user_input:
            return "India"
        return "US"

    def plan(self, user_input: str):

        market = self.detect_market(user_input)

        messages = [
            {
                "role": "system",
                "content": CONTROLLER_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"""
User Request:
{user_input}

Detected Market: {market}

Generate structured execution plan.
"""
            }
        ]

        response = self.llm.generate(messages)

        return response
