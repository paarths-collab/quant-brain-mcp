from __future__ import annotations

import os
import random
import time
from typing import Iterable

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    Groq,
    RateLimitError,
)

from backend.core.config import settings

_LLM_DISABLED_UNTIL = 0.0


def _llm_is_disabled() -> bool:
    return time.time() < _LLM_DISABLED_UNTIL


def _llm_disable_for(seconds: float) -> None:
    global _LLM_DISABLED_UNTIL
    _LLM_DISABLED_UNTIL = max(_LLM_DISABLED_UNTIL, time.time() + max(0.0, float(seconds)))


class LLMClient:

    def __init__(self):
        # Groq Client
        self.groq_api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        self.groq_client = None
        self.llm_enabled = bool(self.groq_api_key)

        # Groq SDK has an internal retry/backoff loop that can sleep for a long time on 429s.
        # Keep it at 0 and implement a short, bounded retry here so websockets don't "hang" for minutes.
        if self.groq_api_key:
            self.groq_client = Groq(api_key=self.groq_api_key, max_retries=0, timeout=20.0)

        self.reasoning_model = os.getenv("GROQ_REASONING_MODEL", "openai/gpt-oss-120b")
        self.fallback_model = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile")
        self.max_reason_tokens = int(os.getenv("GROQ_MAX_REASON_TOKENS", "3072"))
        self.max_search_tokens = int(os.getenv("GROQ_MAX_SEARCH_TOKENS", "2048"))
        self.max_attempts = int(os.getenv("GROQ_MAX_ATTEMPTS", "3"))
        self.max_backoff_s = float(os.getenv("GROQ_MAX_BACKOFF_SECONDS", "8"))
        self.disable_on_error_s = float(os.getenv("GROQ_DISABLE_ON_ERROR_SECONDS", "60"))
        self.disable_on_429_s = float(os.getenv("GROQ_DISABLE_ON_429_SECONDS", "45"))

        # OpenRouter Client (for Reasoning)
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_api_key:
             print("Warning: OPENROUTER_API_KEY not found. Reasoning may fail.")
        
        # We can use the OpenAI SDK for OpenRouter
        from openai import OpenAI
        self.or_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.openrouter_api_key or "sk-dummy"
        )

    def _chat_create_with_backoff(
        self,
        *,
        model: str,
        messages: Iterable[dict],
        max_completion_tokens: int,
        temperature: float,
        top_p: float = 1,
    ):
        if not self.groq_client:
            raise APIConnectionError("GROQ_API_KEY not set; LLM calls disabled.")
        if _llm_is_disabled():
            raise APIConnectionError("LLM temporarily disabled due to recent connection/rate-limit errors.")

        last_err: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                return self.groq_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_completion_tokens,
                    top_p=top_p,
                )
            except RateLimitError as e:
                last_err = e
                if attempt >= self.max_attempts - 1:
                    break
                sleep_s = min(self.max_backoff_s, (1.0 * (2 ** attempt)) + random.random())
                time.sleep(sleep_s)
            except (APITimeoutError, APIConnectionError) as e:
                last_err = e
                if attempt >= self.max_attempts - 1:
                    if self.disable_on_error_s > 0:
                        _llm_disable_for(self.disable_on_error_s)
                    break
                sleep_s = min(self.max_backoff_s, (0.75 * (2 ** attempt)) + random.random())
                time.sleep(sleep_s)
            except APIStatusError as e:
                last_err = e
                # retry a few times on 5xx only
                status = getattr(getattr(e, "response", None), "status_code", None)
                if attempt >= self.max_attempts - 1 or (status is not None and int(status) < 500):
                    break
                sleep_s = min(self.max_backoff_s, (0.75 * (2 ** attempt)) + random.random())
                time.sleep(sleep_s)

        if last_err:
            if isinstance(last_err, RateLimitError) and self.disable_on_429_s > 0:
                _llm_disable_for(self.disable_on_429_s)
            raise last_err
        raise RuntimeError("Groq request failed without an exception")

    def web_search_agent(self, query):
        """
        Uses Groq model with a specific system prompt to act as a Web Search Agent.
        The user wants the model to 'perform websearch' via prompt engineering 
        (or tool calling if we bind it, but let's follow the prompt instruction first).
        """
        messages = [
            {"role": "system", "content": "You are a Web Search Agent. Your goal is to analyze the user's request, perform a deep web search, and provide a comprehensive answer based on real-time data. You are powered by Groq's fast inference. Think step-by-step: 1. Identify search terms. 2. Simulate/Perform search. 3. Synthesize results."},
            {"role": "user", "content": query}
        ]
        
        # We use the same high-performance model for this
        return self._chat_create_with_backoff(
            model=self.reasoning_model,
            messages=messages,
            temperature=0.5,
            max_completion_tokens=self.max_search_tokens,
        )

    def deep_reason(self, messages):
        # Switched to openai/gpt-oss-120b on Groq as requested
        # Note: reasoning_effort param is specific to O1-like models, 
        # but if this model supports it via Groq's API, we pass it.
        # Otherwise, standard completion configuration.
        
        # Using self.groq_client because 'openai/gpt-oss-120b' is hosted on Groq.
        # Try primary model, then a lighter fallback when rate-limited.
        try:
            return self._chat_create_with_backoff(
                model=self.reasoning_model,
                messages=messages,
                temperature=0.5,
                max_completion_tokens=self.max_reason_tokens,
                top_p=1,
            )
        except RateLimitError:
            return self._chat_create_with_backoff(
                model=self.fallback_model,
                messages=messages,
                temperature=0.5,
                max_completion_tokens=min(self.max_reason_tokens, 2048),
                top_p=1,
            )
