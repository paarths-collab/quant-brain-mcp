
import os
import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class GroqAgent:
    """
    Agent for interacting with Groq Cloud API (Llama 3).
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found. GroqAgent may fail.")

    def generate_response(self, prompt: str, model: str = "llama-3.3-70b-versatile", temperature: float = 0.7) -> str:
        """
        Generate a response from Groq.
        """
        if not self.api_key:
            return "Error: GROQ_API_KEY not configured."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Map generic models to Groq specific ones if needed
        if "xiaomi" in model: # Fallback/Substitution
             model = "llama-3.3-70b-versatile" 
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            return f"Error calling Groq API: {str(e)}"

    def run(self, prompt: str, model_name: str = "llama-3.3-70b-versatile") -> str:
        """
        Alias for generate_response to maintain compatibility.
        """
        return self.generate_response(prompt, model=model_name)

    def generate_vision_response(
        self,
        prompt: str,
        image_data_url: str,
        model: str = "llama-3.2-11b-vision-preview",
        temperature: float = 0.2,
    ) -> str:
        """Generate a response from Groq vision model using image + prompt."""
        if not self.api_key:
            return "Error: GROQ_API_KEY not configured."
        if not image_data_url or not image_data_url.startswith("data:image"):
            return "Error: Invalid image payload."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }
            ],
            "temperature": temperature,
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Groq vision API call failed: {e}")
            return f"Error calling Groq vision API: {str(e)}"
