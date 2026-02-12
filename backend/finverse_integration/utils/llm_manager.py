import os
import random
import time
import asyncio
from collections import OrderedDict
from typing import List, Optional, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage

class LLMManager:
    """
    Manages multiple LLM API keys and providers with fallback logic.
    Hierarchy: Gemini Keys (Round Robin/Failover) -> Fallback Provider (Cohere/OpenAI)
    """
    
    def __init__(self, temperature: float = 0.7):
        self.temperature = temperature
        self.gemini_keys = self._load_gemini_keys()
        self.current_key_index = 0
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.cache_enabled = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("LLM_CACHE_TTL", "300"))
        self.cache_max = int(os.getenv("LLM_CACHE_MAX", "128"))
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        
        # Initialize the primary model
        self.primary_llm = self._create_gemini_llm(self.gemini_keys[0]) if self.gemini_keys else None
        
        if not self.primary_llm:
            print("⚠️ No Gemini keys found! Checking fallback providers...")

    def _load_gemini_keys(self) -> List[str]:
        """Load all GEMINI_API_KEY_* from environment"""
        keys = []
        # Check standard key
        if os.getenv("GEMINI_API_KEY"):
            keys.append(os.getenv("GEMINI_API_KEY"))
        
        # Check numbered keys
        i = 1
        while True:
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if not key:
                break
            keys.append(key)
            i += 1
            
        return list(set(keys))  # Remove duplicates

    def _create_gemini_llm(self, api_key: str):
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            google_api_key=api_key,
            convert_system_message_to_human=True
        )

    def _rotate_key(self) -> bool:
        """Switch to the next available Gemini key. Returns True if successful."""
        if len(self.gemini_keys) <= 1:
            return False
        
        self.current_key_index = (self.current_key_index + 1) % len(self.gemini_keys)
        new_key = self.gemini_keys[self.current_key_index]
        print(f"🔄 Switching to Gemini Key #{self.current_key_index + 1}")
        self.primary_llm = self._create_gemini_llm(new_key)
        return True

    def _messages_cache_key(self, messages: List[BaseMessage]) -> str:
        parts = [self.model_name, str(self.temperature)]
        for msg in messages:
            role = msg.__class__.__name__
            content = getattr(msg, "content", "")
            parts.append(f"{role}:{content}")
        return "|".join(parts)

    def _cache_get(self, key: str):
        if not self.cache_enabled:
            return None
        if key not in self._cache:
            return None
        ts, value = self._cache.get(key, (0, None))
        if (time.time() - ts) > self.cache_ttl:
            self._cache.pop(key, None)
            return None
        # refresh LRU
        self._cache.move_to_end(key, last=True)
        return value

    def _cache_set(self, key: str, value: Any) -> None:
        if not self.cache_enabled:
            return
        self._cache[key] = (time.time(), value)
        self._cache.move_to_end(key, last=True)
        if len(self._cache) > self.cache_max:
            self._cache.popitem(last=False)

    async def ainvoke(self, messages):
        """Async wrapper for invoke"""
        try:
             # Try native async if available
             cache_key = self._messages_cache_key(messages)
             cached = self._cache_get(cache_key)
             if cached is not None:
                 return cached

             if hasattr(self.primary_llm, 'ainvoke'):
                 result = await self.primary_llm.ainvoke(messages)
                 self._cache_set(cache_key, result)
                 return result
             else:
                 # Fallback to sync in thread
                 return await asyncio.to_thread(self.invoke, messages)
        except Exception as e:
             # Fallback
             return await asyncio.to_thread(self.invoke, messages)

    def invoke(self, messages: List[BaseMessage]) -> Any:
        """Reliable invoke with failover logic"""
        cache_key = self._messages_cache_key(messages)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        max_retries = len(self.gemini_keys) + 1  # Try all keys + 1 retry
        
        for attempt in range(max_retries):
            try:
                if not self.primary_llm:
                    raise Exception("No Primary LLM available")
                
                result = self.primary_llm.invoke(messages)
                self._cache_set(cache_key, result)
                return result
                
            except Exception as e:
                error_str = str(e).lower()
                # Check for rate limit or quota errors
                if "429" in error_str or "quota" in error_str or "resource exhausted" in error_str:
                    print(f"⚠️ Quota/Rate Limit hit on key #{self.current_key_index + 1}. Attempting switch...")
                    if self._rotate_key():
                        time.sleep(1)  # Brief pause before retry
                        continue
                    else:
                        print("❌ All Gemini keys exhausted. Use more keys in .env (GEMINI_API_KEY_3, etc.)")
                        raise e
                else:
                    # For non-quota errors, maybe simply retry or raise
                    print(f"❌ LLM Error: {e}")
                    raise e
                    
        raise Exception("Max retries exceeded for LLM invocation")
