from backend.backend1.core.llm_client import LLMClient


class WebSearchAgent:

    def __init__(self):
        self.llm = LLMClient()

    def run(self, query: str, state=None):

        # Only pass small optimized query
        messages = [
            {
                "role": "user",
                "content": query[:500]  # Hard limit to prevent 413
            }
        ]

        result = self.llm.run_model(
            model="compound",
            messages=messages
        )

        return {
            "query": query,
            "summary": result[:2000] if result else "No result" # Prevent giant state
        }
