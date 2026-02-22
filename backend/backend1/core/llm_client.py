from groq import Groq
import os


class LLMClient:

    def __init__(self):
        # Robustly load env if not present
        if not os.getenv("GROQ_API_KEY"):
            from dotenv import load_dotenv
            # Try loading from backend/.env (assuming we are in backend/backend1/core/)
            # ../../../.env from file location
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
            load_dotenv(env_path)
            
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def run_model(
        self,
        model,
        messages,
        temperature=0.3,
        max_tokens=1500,
        tools_enabled=False
    ):

        if model == "compound":
            return self._run_compound(messages)

        elif model == "validator":
            return self._run_validator(messages)
            
        elif model == "deep_reason":
            return self._run_deep_reason(messages)

        else:
            raise ValueError(f"Unknown model type: {model}")

    def _run_compound(self, messages):

        completion = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_completion_tokens=500
        )

        return completion.choices[0].message.content

    def _run_validator(self, messages):

        completion = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.2,
            max_completion_tokens=1500,
            top_p=1,
            # reasoning_effort="medium" # Commented out as support varies, user can enable if needed
        )

        return completion.choices[0].message.content

    # Keep generate for backward compatibility with existing tests if needed, or remove
    def generate(self, messages, temperature=0.3, max_tokens=1500):
        return self.run_model("validator", messages, temperature, max_tokens)

    def _run_deep_reason(self, messages):
        # Use high-capacity model
        completion = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4,
            max_completion_tokens=4096
        )
        return completion.choices[0].message.content
