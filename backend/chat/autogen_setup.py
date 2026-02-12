"""
AutoGen setup with Gemini/Groq LLM backends.
Provides multi-agent conversation capabilities for investment research.
"""

import os
import logging
from typing import Optional, Tuple, Any
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Try to import AutoGen components
try:
    from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    AUTOGEN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AutoGen imports failed: {e}")
    AUTOGEN_AVAILABLE = False
    AssistantAgent = None
    UserProxyAgent = None
    OpenAIChatCompletionClient = None


def _get_gemini_client() -> Optional[Any]:
    """Create Gemini model client using OpenAI-compatible endpoint."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    
    # Gemini's OpenAI-compatible endpoint
    return OpenAIChatCompletionClient(
        model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )


def _get_groq_client() -> Optional[Any]:
    """Create Groq model client."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    
    return OpenAIChatCompletionClient(
        model="llama-3.1-70b-versatile",
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )


def _get_openai_client() -> Optional[Any]:
    """Create OpenAI model client (fallback)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    
    return OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=api_key
    )


def get_model_client() -> Tuple[Optional[Any], str]:
    """
    Get the best available model client.
    Priority: Gemini -> Groq -> OpenAI
    
    Returns:
        Tuple of (client, provider_name)
    """
    # Try Gemini first (free tier available)
    client = _get_gemini_client()
    if client:
        return client, "gemini"
    
    # Try Groq (free tier with limits)
    client = _get_groq_client()
    if client:
        return client, "groq"
    
    # Try OpenAI (paid)
    client = _get_openai_client()
    if client:
        return client, "openai"
    
    return None, "none"


INVESTMENT_ADVISOR_PROMPT = """You are a cautious, experienced financial advisor assistant.

Your core principles:
1. NEVER give direct buy/sell commands - always frame as considerations
2. Always explain risks before potential rewards
3. Ask clarifying questions about time horizon, risk tolerance, goals
4. Defer to structured analysis from the system's pipelines
5. When emotions are detected (panic, FOMO, greed), prioritize calming guidance
6. Reference historical patterns but acknowledge past performance ≠ future results

When responding:
- Be empathetic but data-driven
- Use bullet points for key considerations
- Highlight red flags prominently
- End with 1-2 clarifying questions when appropriate

You have access to:
- Real-time market data from yfinance
- News sentiment from DuckDuckGo
- Technical indicators and volatility metrics
- Emotion detection system

Remember: Your role is to help users make INFORMED decisions, not to make decisions for them."""


def init_autogen() -> Tuple[Optional[Any], Optional[Any], str]:
    """
    Initialize AutoGen agents with the best available LLM.
    
    Returns:
        Tuple of (assistant_agent, user_proxy, provider_name)
        Returns (None, None, "unavailable") if no LLM available
    """
    if not AUTOGEN_AVAILABLE:
        logger.warning("AutoGen not available - imports failed")
        return None, None, "unavailable"
    
    model_client, provider = get_model_client()
    
    if not model_client:
        logger.warning("No LLM API key found (GEMINI_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY)")
        return None, None, "no_api_key"
    
    try:
        assistant = AssistantAgent(
            name="investment_advisor",
            model_client=model_client,
            system_message=INVESTMENT_ADVISOR_PROMPT
        )
        
        user = UserProxyAgent(name="user")
        
        logger.info(f"AutoGen initialized successfully with {provider}")
        return assistant, user, provider
        
    except Exception as e:
        logger.error(f"Failed to initialize AutoGen agents: {e}")
        return None, None, f"error:{e}"


# Module-level initialization for optional use
_cached_agents = None

def get_agents():
    """Get cached AutoGen agents (lazy initialization)."""
    global _cached_agents
    if _cached_agents is None:
        _cached_agents = init_autogen()
    return _cached_agents
