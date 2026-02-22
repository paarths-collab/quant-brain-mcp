from groq import Groq
import os

class LLMClient:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def run_reasoning(self, messages, max_tokens=4096):
        """Run deep reasoning using gpt-oss-120b"""
        completion = self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.3,
            max_completion_tokens=max_tokens,
            top_p=1
        )
        return completion.choices[0].message.content

    def run_search_summary(self, query, search_results):
        """Summarize search results using gpt-oss-120b (No Tools)"""
        context = str(search_results)[:6000] # Truncate context
        
        messages = [
            {
                "role": "system", 
                "content": "You are a research analyst. Summarize the provided search results to answer the user query."
            },
            {
                "role": "user",
                "content": f"Query: {query}\n\nResults: {context}"
            }
        ]
        
        completion = self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.2,
            max_completion_tokens=2000
        )
        return completion.choices[0].message.content
