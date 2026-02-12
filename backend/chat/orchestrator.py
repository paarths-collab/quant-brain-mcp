"""
Chat Orchestrator - AutoGen-based Human-in-the-Loop Agent System
Manages conversation flow, intent clarification, and pipeline execution.
"""
import os
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# AutoGen configuration
USE_AUTOGEN = True  # Enable AutoGen features

# Import AutoGen via centralized setup
try:
    from .autogen_setup import init_autogen, AUTOGEN_AVAILABLE, get_model_client
except ImportError:
    AUTOGEN_AVAILABLE = False
    init_autogen = None
    get_model_client = None
    print("⚠️ AutoGen setup not available - using lightweight orchestration")

# Import our components
from .intent_router import IntentRouter, UserIntent, PipelineType, get_intent_router
from .pipelines import PipelineManager, PipelineResult, get_pipeline_manager

try:
    from autogen_core.models import SystemMessage, UserMessage
except Exception:
    SystemMessage = None
    UserMessage = None

import re


class ConversationState(str, Enum):
    """Conversation states for the state machine"""
    IDLE = "idle"
    AWAITING_INTENT = "awaiting_intent"
    CLARIFYING = "clarifying"
    CONFIRMING = "confirming"
    EXECUTING = "executing"
    COMPLETE = "complete"


@dataclass
class Message:
    """Chat message"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Tracks conversation state and history"""
    session_id: str
    user_id: str = "default"
    state: ConversationState = ConversationState.IDLE
    messages: List[Message] = field(default_factory=list)
    current_intent: Optional[UserIntent] = None
    pending_confirmation: bool = False
    confirmed_pipelines: List[PipelineType] = field(default_factory=list)
    results: Dict[str, PipelineResult] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add a message to history"""
        self.messages.append(Message(
            role=role,
            content=content,
            metadata=metadata or {}
        ))
    
    def get_history_text(self, limit: int = 10) -> str:
        """Get recent history as text"""
        recent = self.messages[-limit:]
        return "\n".join([f"{m.role}: {m.content}" for m in recent])


class ChatOrchestrator:
    """
    Main orchestrator for the multi-agent chat system.
    
    Flow:
    1. User sends message
    2. IntentRouter analyzes intent
    3. If clarification needed → ask user
    4. If confident → confirm with user before executing
    5. User confirms → run pipelines
    6. Return combined results
    """
    
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        auto_confirm: bool = False  # Skip confirmation for high-confidence intents
    ):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.auto_confirm = auto_confirm
        
        # Core components
        self.intent_router = get_intent_router()
        self.pipeline_manager = get_pipeline_manager()
        
        # Active conversations (session_id -> context)
        self.conversations: Dict[str, ConversationContext] = {}
        
        # Streaming callback (set by WebSocket handler)
        self.stream_callback: Optional[Callable[[str, str], None]] = None
        
        # Initialize AutoGen if available
        self._init_autogen_agents()
    
    def _init_autogen_agents(self):
        """Initialize AutoGen agents using centralized setup (Gemini/Groq/OpenAI)"""
        if not AUTOGEN_AVAILABLE or not init_autogen:
            self.assistant = None
            self.user_proxy = None
            self.autogen_provider = "unavailable"
            return
        
        try:
            self.assistant, self.user_proxy, self.autogen_provider = init_autogen()
            
            if self.assistant:
                print(f"✅ AutoGen initialized with {self.autogen_provider}")
            else:
                print(f"⚠️ AutoGen agents not initialized: {self.autogen_provider}")
                
        except Exception as e:
            print(f"⚠️ Failed to initialize AutoGen agents: {e}")
            self.assistant = None
            self.user_proxy = None
            self.autogen_provider = f"error:{e}"
    
    def get_or_create_conversation(
        self,
        session_id: str,
        user_id: str = "default"
    ) -> ConversationContext:
        """Get existing or create new conversation context"""
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationContext(
                session_id=session_id,
                user_id=user_id
            )
        return self.conversations[session_id]
    
    async def process_message(
        self,
        session_id: str,
        user_message: str,
        user_id: str = "default"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message and yield response chunks.
        
        Yields:
            Dict with keys: type, content, metadata
            Types: "text", "thinking", "result", "confirmation", "error"
        """
        ctx = self.get_or_create_conversation(session_id, user_id)
        ctx.add_message("user", user_message)
        
        try:
            # State machine handling
            if ctx.state == ConversationState.IDLE:
                async for chunk in self._handle_new_message(ctx, user_message):
                    yield chunk
                    
            elif ctx.state == ConversationState.CLARIFYING:
                async for chunk in self._handle_clarification_response(ctx, user_message):
                    yield chunk
                    
            elif ctx.state == ConversationState.CONFIRMING:
                async for chunk in self._handle_confirmation_response(ctx, user_message):
                    yield chunk
                    
            else:
                yield {
                    "type": "text",
                    "content": "I'm ready for your next question!",
                    "metadata": {"state": ctx.state.value}
                }
                ctx.state = ConversationState.IDLE
                
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Sorry, I encountered an error: {str(e)}",
                "metadata": {"error": str(e)}
            }
            ctx.state = ConversationState.IDLE
    
    async def _handle_new_message(
        self,
        ctx: ConversationContext,
        message: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle a new user message"""
        # Quick greeting check (no pipeline needed)
        if self._is_greeting(message):
            greeting = "Hi! 👋 Tell me which stock or portfolio you want to analyze, or describe your investing goal."
            yield {"type": "text", "content": greeting, "metadata": {"greeting": True}}
            ctx.add_message("assistant", greeting)
            ctx.state = ConversationState.IDLE
            return

        # Analyze intent
        yield {
            "type": "thinking",
            "content": "🤔 Analyzing your request...",
            "metadata": {}
        }
        
        intent = self.intent_router.analyze(message)
        ctx.current_intent = intent

        # If no ticker detected but stock-related pipelines are needed, ask LLM to infer ticker
        if not intent.detected_ticker and any(
            p in intent.pipelines_needed for p in [PipelineType.STOCK_INFO, PipelineType.EMOTION, PipelineType.COMBINED]
        ):
            llm_ticker, llm_market = await self._llm_detect_ticker(message)
            if llm_ticker:
                intent.detected_ticker = llm_ticker
                if llm_market:
                    intent.detected_market = llm_market
                ctx.current_intent = intent
        
        # If clarification needed
        if intent.clarification_needed:
            ctx.state = ConversationState.CLARIFYING
            yield {
                "type": "clarification",
                "content": intent.clarification_question,
                "metadata": {
                    "detected_ticker": intent.detected_ticker,
                    "confidence": intent.confidence
                }
            }
            ctx.add_message("assistant", intent.clarification_question)
            return
        
        # If confident enough, ask for confirmation (or auto-confirm)
        if intent.confidence >= 0.7 and self.auto_confirm:
            # Auto-confirm and execute
            async for chunk in self._execute_pipelines(ctx):
                yield chunk
        else:
            # Ask for confirmation
            ctx.state = ConversationState.CONFIRMING
            confirmation_msg = self._create_confirmation_message(intent)
            yield {
                "type": "confirmation",
                "content": confirmation_msg,
                "metadata": {
                    "ticker": intent.detected_ticker,
                    "market": intent.detected_market,
                    "pipelines": [p.value for p in intent.pipelines_needed],
                    "confidence": intent.confidence
                }
            }
            ctx.add_message("assistant", confirmation_msg)
    
    async def _handle_clarification_response(
        self,
        ctx: ConversationContext,
        response: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle user's response to clarification question"""
        
        # Update intent with clarification
        ctx.current_intent = self.intent_router.parse_clarification_response(
            response, ctx.current_intent
        )
        
        if ctx.current_intent.clarification_needed:
            # Still need more info
            yield {
                "type": "clarification",
                "content": ctx.current_intent.clarification_question,
                "metadata": {}
            }
            ctx.add_message("assistant", ctx.current_intent.clarification_question)
        else:
            # Got enough info, ask for confirmation
            ctx.state = ConversationState.CONFIRMING
            confirmation_msg = self._create_confirmation_message(ctx.current_intent)
            yield {
                "type": "confirmation",
                "content": confirmation_msg,
                "metadata": {
                    "ticker": ctx.current_intent.detected_ticker,
                    "pipelines": [p.value for p in ctx.current_intent.pipelines_needed]
                }
            }
            ctx.add_message("assistant", confirmation_msg)
    
    async def _handle_confirmation_response(
        self,
        ctx: ConversationContext,
        response: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle user's confirmation response"""
        response_lower = response.lower().strip()

        # Market toggle handling
        if response_lower in {"us", "usa", "united states"}:
            if ctx.current_intent:
                ctx.current_intent.detected_market = "US"
            confirmation_msg = self._create_confirmation_message(ctx.current_intent)
            yield {"type": "confirmation", "content": confirmation_msg, "metadata": {"market": "US"}}
            ctx.add_message("assistant", confirmation_msg)
            return

        if response_lower in {"in", "india", "nse", "bse"}:
            if ctx.current_intent:
                ctx.current_intent.detected_market = "IN"
            confirmation_msg = self._create_confirmation_message(ctx.current_intent)
            yield {"type": "confirmation", "content": confirmation_msg, "metadata": {"market": "IN"}}
            ctx.add_message("assistant", confirmation_msg)
            return

        # Ticker correction during confirmation
        if ctx.current_intent:
            ticker, market = self.intent_router._extract_ticker(response)  # reuse router logic
            if ticker:
                ctx.current_intent.detected_ticker = ticker
                if market:
                    ctx.current_intent.detected_market = market
                confirmation_msg = self._create_confirmation_message(ctx.current_intent)
                yield {"type": "confirmation", "content": confirmation_msg, "metadata": {"ticker": ticker, "market": market}}
                ctx.add_message("assistant", confirmation_msg)
                return
        
        # Check for affirmative
        affirmative = ["yes", "y", "yeah", "yep", "sure", "ok", "okay", "go", "do it", "proceed", "confirm", "run", "execute", "1"]
        negative = ["no", "n", "nope", "cancel", "stop", "wait", "nevermind", "0"]
        
        if any(word in response_lower for word in affirmative):
            # If ticker still missing for stock/emotion, ask explicitly
            ticker_required = any(
                p in ctx.current_intent.pipelines_needed
                for p in [PipelineType.STOCK_INFO, PipelineType.EMOTION, PipelineType.COMBINED]
            )
            if ticker_required and not ctx.current_intent.detected_ticker:
                ctx.state = ConversationState.CLARIFYING
                prompt = "Please confirm the stock ticker (e.g., AAPL, TSLA, RELIANCE, TCS)."
                yield {"type": "clarification", "content": prompt, "metadata": {}}
                ctx.add_message("assistant", prompt)
                return

            # User confirmed - execute pipelines
            async for chunk in self._execute_pipelines(ctx):
                yield chunk
                
        elif any(word in response_lower for word in negative):
            # User cancelled
            ctx.state = ConversationState.IDLE
            yield {
                "type": "text",
                "content": "No problem! Let me know when you're ready, or tell me what you'd like to do instead.",
                "metadata": {"cancelled": True}
            }
            ctx.add_message("assistant", "Cancelled. Ready for new request.")
            
        else:
            # Unclear response - treat as new intent
            new_intent = self.intent_router.analyze(response)
            if new_intent.detected_ticker or new_intent.pipelines_needed:
                ctx.current_intent = new_intent
                confirmation_msg = self._create_confirmation_message(new_intent)
                yield {
                    "type": "confirmation",
                    "content": confirmation_msg,
                    "metadata": {}
                }
                ctx.add_message("assistant", confirmation_msg)
            else:
                yield {
                    "type": "text",
                    "content": "Just reply **yes** to proceed or **no** to cancel. Or tell me what you'd like to do instead!",
                    "metadata": {}
                }
    
    async def _execute_pipelines(
        self,
        ctx: ConversationContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the confirmed pipelines"""
        ctx.state = ConversationState.EXECUTING
        intent = ctx.current_intent

        if not intent:
            yield {
                "type": "error",
                "content": "I need a bit more context. What would you like me to analyze?",
                "metadata": {}
            }
            ctx.state = ConversationState.CLARIFYING
            return

        ticker_required = any(
            p in intent.pipelines_needed
            for p in [PipelineType.STOCK_INFO, PipelineType.EMOTION, PipelineType.COMBINED]
        )

        if ticker_required and not intent.detected_ticker:
            yield {
                "type": "error",
                "content": "I need a stock ticker to analyze. What stock are you interested in?",
                "metadata": {}
            }
            ctx.state = ConversationState.CLARIFYING
            return
        
        run_label = intent.detected_ticker or "your request"
        yield {
            "type": "thinking",
            "content": f"🚀 Running analysis for **{run_label}**...",
            "metadata": {"pipelines": [p.value for p in intent.pipelines_needed]}
        }
        
        # Determine which pipelines to run
        pipeline_names = []
        for p in intent.pipelines_needed:
            if p == PipelineType.COMBINED:
                continue  # This is just a marker
            pipeline_names.append(p.value)
        
        if not pipeline_names:
            pipeline_names = ["stock_info"]  # Default
        
        # Run pipelines
        if len(pipeline_names) > 1:
            results = await self.pipeline_manager.run_combined_pipeline(
                ticker=intent.detected_ticker,
                user_message=intent.raw_message,
                market=intent.detected_market,
                user_id=ctx.user_id,
                pipelines=pipeline_names
            )
        else:
            # Single pipeline
            pipeline = pipeline_names[0]
            if pipeline == "emotion":
                result = await self.pipeline_manager.run_emotion_pipeline(
                    ticker=intent.detected_ticker,
                    user_message=intent.raw_message,
                    market=intent.detected_market,
                    user_id=ctx.user_id
                )
            elif pipeline == "wealth":
                result = await self.pipeline_manager.run_wealth_pipeline(
                    user_input=intent.raw_message,
                    market=intent.detected_market
                )
            else:
                result = await self.pipeline_manager.run_stock_info_pipeline(
                    ticker=intent.detected_ticker,
                    market=intent.detected_market,
                    user_message=intent.raw_message
                )
            results = {pipeline: result}
        
        # Store results
        ctx.results = results
        
        # Yield results with Gemini-enhanced formatting
        for name, result in results.items():
            # Try Gemini formatting for better output
            if result.success and hasattr(self.pipeline_manager, 'format_with_gemini'):
                try:
                    formatted_summary = await self.pipeline_manager.format_with_gemini(
                        pipeline_type=name,
                        raw_data=result.data,
                        user_message=intent.raw_message
                    )
                except Exception:
                    formatted_summary = result.summary
            else:
                formatted_summary = result.summary
            
            yield {
                "type": "result",
                "content": formatted_summary,
                "metadata": {
                    "pipeline": name,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "data": result.data if result.success else None,
                    "gemini_formatted": formatted_summary != result.summary
                }
            }
        
        # Final message
        ctx.state = ConversationState.COMPLETE
        yield {
            "type": "text",
            "content": "\n---\n✅ Analysis complete! Ask me anything else or request a different analysis.",
            "metadata": {"complete": True}
        }
        
        ctx.add_message("assistant", f"Analysis complete for {intent.detected_ticker}")
        ctx.state = ConversationState.IDLE
    
    def _create_confirmation_message(self, intent: UserIntent) -> str:
        """Create a confirmation message for the user"""
        if PipelineType.WEALTH in intent.pipelines_needed and not intent.detected_ticker:
            ticker = "your portfolio"
        else:
            ticker = intent.detected_ticker or "the stock"
        market_emoji = "🇮🇳" if intent.detected_market == "IN" else "🇺🇸"
        
        # Build pipeline list
        pipeline_descriptions = {
            PipelineType.EMOTION: "🧠 Emotional Trading Check",
            PipelineType.STOCK_INFO: "📊 Stock Analysis",
            PipelineType.WEALTH: "💰 Wealth Advice",
            PipelineType.INTENT: "🎯 Intent Analysis",
            PipelineType.COMBINED: "📋 Full Analysis"
        }
        
        pipelines_text = "\n".join([
            f"  • {pipeline_descriptions.get(p, p.value)}"
            for p in intent.pipelines_needed
            if p != PipelineType.COMBINED
        ])
        
        if intent.user_emotion:
            emotion_note = f"\n\n⚠️ I noticed some **{intent.user_emotion}** in your message. I'll help you think through this rationally."
        else:
            emotion_note = ""
        
        return f"""I understand you want to analyze **{ticker}** {market_emoji}

**I'll run:**
{pipelines_text}{emotion_note}

**Market:** {intent.detected_market} (reply **US** or **IN** to switch)

**Ready to proceed?** (yes/no)"""

    def _is_greeting(self, message: str) -> bool:
        text = message.strip().lower()
        if not text:
            return False
        greetings = {"hi", "hello", "hey", "yo", "sup", "good morning", "good afternoon", "good evening"}
        if text in greetings:
            return True
        # Short greeting phrases like "hi there", "hello!"
        tokens = [t for t in re.split(r'\W+', text) if t]
        if len(tokens) <= 3 and any(t in {"hi", "hello", "hey"} for t in tokens):
            return True
        return False

    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session"""
        if session_id not in self.conversations:
            return []
        return [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp
            }
            for m in self.conversations[session_id].messages
        ]
    
    def clear_conversation(self, session_id: str):
        """Clear a conversation"""
        if session_id in self.conversations:
            del self.conversations[session_id]

    async def _llm_detect_ticker(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Ask Gemini/Groq/OpenAI to infer the most likely stock ticker from the user message.
        Returns (ticker, market) or (None, None) if unknown.
        """
        if not get_model_client or SystemMessage is None or UserMessage is None:
            return None, None

        client, _provider = get_model_client()
        if not client:
            return None, None

        system_prompt = (
            "You are a stock ticker extraction assistant. "
            "Given a user message, return ONLY the most likely stock ticker symbol. "
            "Use format like AAPL or RELIANCE.NS when appropriate. "
            "If unsure, return NONE."
        )

        try:
            result = await client.create(messages=[
                SystemMessage(content=system_prompt, source="system"),
                UserMessage(content=message, source="user")
            ])
            content = result.content if isinstance(result.content, str) else str(result.content)
        except Exception:
            return None, None

        text = content.strip().upper()
        if not text or text in {"NONE", "N/A", "UNKNOWN"}:
            return None, None

        m = re.search(r'\b([A-Z0-9]{1,10}(?:\.(NS|BO))?)\b', text)
        if not m:
            return None, None

        symbol = m.group(1)
        market = "IN" if symbol.endswith(".NS") or symbol.endswith(".BO") else "US"

        # Normalize IN tickers to base symbol (format_ticker will add .NS later)
        if market == "IN":
            symbol = symbol.split(".")[0]

        return symbol, market


# Singleton instance
_orchestrator: Optional[ChatOrchestrator] = None

def get_chat_orchestrator(auto_confirm: bool = False) -> ChatOrchestrator:
    """Get singleton ChatOrchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ChatOrchestrator(auto_confirm=auto_confirm)
    return _orchestrator
