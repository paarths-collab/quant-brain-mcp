"""
Stock Advisor API — Auto-recommend & Multi-POV Analysis.
Uses LangGraph for the 3-agent POV workflow.

Routes:
  POST /api/stock-advisor/recommend  — profile-driven stock recommendation
  POST /api/stock-advisor/multi-pov  — 3 agents (Gemini/Groq/DeepSeek) analyze a stock
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.database.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stock-advisor", tags=["Stock Advisor"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RecommendRequest(BaseModel):
    user_input: str = Field(..., description="User's investment query")
    user_id: str = Field(default="default")
    market: str = Field(default="US")


class MultiPovRequest(BaseModel):
    symbol: str = Field(..., description="Stock ticker to analyze")
    market: str = Field(default="US")
    context: Optional[str] = Field(default=None, description="Extra context from user")


class AgentPov(BaseModel):
    agent: str
    provider: str
    verdict: str
    confidence: float
    reasoning: str
    key_factors: List[str]


class MultiPovResponse(BaseModel):
    symbol: str
    bull: AgentPov
    bear: AgentPov
    neutral: AgentPov


# ---------------------------------------------------------------------------
# LLM Helpers — one per provider
# ---------------------------------------------------------------------------

def _call_gemini(prompt: str) -> str:
    """Call Google Gemini via google-generativeai SDK."""
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "[Gemini unavailable — no API key]"
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.warning(f"Gemini call failed: {e}")
        return f"[Gemini error: {e}]"


def _call_groq(prompt: str) -> str:
    """Call Groq LLM."""
    try:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "[Groq unavailable — no API key]"
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"Groq call failed: {e}")
        return f"[Groq error: {e}]"


def _call_qwen(prompt: str) -> str:
    """Call Qwen via OpenRouter (replaces DeepSeek)."""
    try:
        import httpx
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return "[Qwen unavailable — no OpenRouter key]"
        model = "qwen/qwen3-vl-235b-a22b-thinking"
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2048,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"Qwen/OpenRouter call failed: {e}")
        return f"[Qwen error: {e}]"


# ---------------------------------------------------------------------------
# Multi-POV LangGraph Workflow
# ---------------------------------------------------------------------------

def _build_pov_prompt(symbol: str, market: str, role: str, context: str = "") -> str:
    """Create a role-specific prompt for a POV agent."""
    role_instructions = {
        "bull": (
            "You are the BULL analyst — an optimistic investment advisor. "
            "Find EVERY reason why someone SHOULD buy this stock. "
            "Focus on growth catalysts, competitive moats, positive momentum, "
            "strong fundamentals, and upside potential. Be enthusiastic but backed by data."
        ),
        "bear": (
            "You are the BEAR analyst — a cautious, risk-focused investment advisor. "
            "Find EVERY reason why someone should AVOID or SELL this stock. "
            "Focus on risks, overvaluation, competitive threats, weak fundamentals, "
            "regulatory headwinds, and downside scenarios. Be thorough and skeptical."
        ),
        "neutral": (
            "You are the NEUTRAL analyst — a balanced, data-driven investment advisor. "
            "Provide an UNBIASED assessment of this stock. Weigh both pros and cons equally. "
            "Focus on fair valuation, risk-adjusted returns, sector positioning, "
            "and what type of investor this is suitable for. Be measured and objective."
        ),
    }

    extra = f"\nAdditional context from user: {context}" if context else ""

    return f"""
{role_instructions[role]}

Analyze the stock: {symbol} (Market: {market}){extra}

Respond in this EXACT format (no markdown, no extra text):
VERDICT: [BUY/SELL/HOLD — one word]
CONFIDENCE: [0.0 to 1.0]
REASONING: [2-4 sentences explaining your position]
KEY_FACTORS:
- [factor 1]
- [factor 2]
- [factor 3]
- [factor 4]
"""


def _parse_pov_response(raw: str, agent_name: str, provider: str) -> AgentPov:
    """Parse a structured POV response into an AgentPov model."""
    lines = raw.strip().split("\n")
    verdict = "HOLD"
    confidence = 0.5
    reasoning = ""
    key_factors: List[str] = []
    in_factors = False

    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("VERDICT:"):
            verdict = stripped.split(":", 1)[1].strip().upper()
            if verdict not in ("BUY", "SELL", "HOLD"):
                verdict = "HOLD"
        elif stripped.upper().startswith("CONFIDENCE:"):
            try:
                confidence = float(stripped.split(":", 1)[1].strip())
                confidence = max(0.0, min(1.0, confidence))
            except ValueError:
                confidence = 0.5
        elif stripped.upper().startswith("REASONING:"):
            reasoning = stripped.split(":", 1)[1].strip()
        elif stripped.upper().startswith("KEY_FACTORS:"):
            in_factors = True
        elif in_factors and stripped.startswith("-"):
            key_factors.append(stripped.lstrip("- ").strip())
        elif not in_factors and not stripped.startswith(("VERDICT", "CONFIDENCE", "KEY_FACTORS")):
            # continuation of reasoning
            if reasoning and not stripped.upper().startswith("KEY_FACTORS"):
                reasoning += " " + stripped

    if not reasoning:
        reasoning = raw[:300]
    if not key_factors:
        key_factors = ["Analysis provided — see reasoning for details"]

    return AgentPov(
        agent=agent_name,
        provider=provider,
        verdict=verdict,
        confidence=confidence,
        reasoning=reasoning,
        key_factors=key_factors[:6],
    )


def _run_multi_pov_langgraph(symbol: str, market: str, context: str = "") -> Dict[str, Any]:
    """
    Run a LangGraph-style stateful workflow:
      Node 1 (Bull / Gemini) → Node 2 (Bear / Groq) → Node 3 (Neutral / DeepSeek)
    Each node runs in sequence, adding its result to the shared state.
    """
    try:
        from langgraph.graph import StateGraph, END
        from typing import TypedDict

        class PovState(TypedDict):
            symbol: str
            market: str
            context: str
            bull: Optional[dict]
            bear: Optional[dict]
            neutral: Optional[dict]

        def bull_node(state: PovState) -> PovState:
            prompt = _build_pov_prompt(state["symbol"], state["market"], "bull", state["context"])
            raw = _call_gemini(prompt)
            pov = _parse_pov_response(raw, "Bull Analyst", "Gemini")
            state["bull"] = pov.model_dump()
            return state

        def bear_node(state: PovState) -> PovState:
            prompt = _build_pov_prompt(state["symbol"], state["market"], "bear", state["context"])
            raw = _call_groq(prompt)
            pov = _parse_pov_response(raw, "Bear Analyst", "Groq")
            state["bear"] = pov.model_dump()
            return state

        def neutral_node(state: PovState) -> PovState:
            prompt = _build_pov_prompt(state["symbol"], state["market"], "neutral", state["context"])
            raw = _call_qwen(prompt)
            pov = _parse_pov_response(raw, "Neutral Analyst", "Qwen")
            state["neutral"] = pov.model_dump()
            return state

        # Build graph
        graph = StateGraph(PovState)
        graph.add_node("bull_analysis", bull_node)
        graph.add_node("bear_analysis", bear_node)
        graph.add_node("neutral_analysis", neutral_node)
        graph.set_entry_point("bull_analysis")
        graph.add_edge("bull_analysis", "bear_analysis")
        graph.add_edge("bear_analysis", "neutral_analysis")
        graph.add_edge("neutral_analysis", END)

        compiled = graph.compile()
        result = compiled.invoke({
            "symbol": symbol,
            "market": market,
            "context": context or "",
            "bull": None,
            "bear": None,
            "neutral": None,
        })
        return result

    except ImportError:
        logger.warning("LangGraph not available, falling back to sequential calls")
        # Fallback — run sequentially without langgraph
        bull_prompt = _build_pov_prompt(symbol, market, "bull", context)
        bear_prompt = _build_pov_prompt(symbol, market, "bear", context)
        neutral_prompt = _build_pov_prompt(symbol, market, "neutral", context)

        bull_raw = _call_gemini(bull_prompt)
        bear_raw = _call_groq(bear_prompt)
        neutral_raw = _call_qwen(neutral_prompt)

        return {
            "symbol": symbol,
            "bull": _parse_pov_response(bull_raw, "Bull Analyst", "Gemini").model_dump(),
            "bear": _parse_pov_response(bear_raw, "Bear Analyst", "Groq").model_dump(),
            "neutral": _parse_pov_response(neutral_raw, "Neutral Analyst", "Qwen").model_dump(),
        }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/recommend")
async def recommend(request: RecommendRequest, db=Depends(get_db)):
    """
    Auto-recommend stocks: reads saved profile, combines with user input,
    and runs through WealthOrchestrator.
    """
    try:
        # 1. Load user profile from DB
        row = db.execute(
            text("SELECT * FROM user_profiles WHERE user_id = :uid"),
            {"uid": request.user_id},
        ).mappings().first()

        profile_context = ""
        if row:
            p = dict(row)
            parts = []
            if p.get("age"):
                parts.append(f"I am {p['age']} years old")
            if p.get("monthly_income"):
                parts.append(f"earning ${p['monthly_income']}/month")
            if p.get("monthly_savings"):
                parts.append(f"saving ${p['monthly_savings']}/month")
            if p.get("risk_tolerance"):
                parts.append(f"with {p['risk_tolerance']} risk tolerance")
            if p.get("horizon_years"):
                parts.append(f"for a {p['horizon_years']}-year horizon")
            if p.get("primary_goal"):
                parts.append(f"goal: {p['primary_goal']}")
            if p.get("existing_investments"):
                parts.append(f"existing: {p['existing_investments']}")
            profile_context = ", ".join(parts) + ". "

        # 2. Combine profile + user input
        combined_input = profile_context + request.user_input

        # 3. Run through WealthOrchestrator
        from backend.finverse_integration.routes.wealth_routes import (
            get_wealth_manager,
            map_wealth_state_to_response,
        )
        manager = get_wealth_manager()
        timeout_sec = float(os.getenv("WEALTH_TIMEOUT_SEC", "240"))
        result = await asyncio.wait_for(
            manager.run_workflow(
                user_input=combined_input,
                market=request.market,
            ),
            timeout=timeout_sec,
        )
        return map_wealth_state_to_response(result)

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Analysis timed out")
    except Exception as e:
        logger.exception("Recommend failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-pov")
def multi_pov_analysis(request: MultiPovRequest):
    """
    3 agents (Gemini / Groq / DeepSeek) analyze a stock and return
    differing perspectives: Bull, Bear, Neutral.
    Uses LangGraph for the agentic workflow.
    """
    try:
        result = _run_multi_pov_langgraph(
            symbol=request.symbol,
            market=request.market,
            context=request.context or "",
        )
        return {
            "symbol": request.symbol,
            "bull": result.get("bull", {}),
            "bear": result.get("bear", {}),
            "neutral": result.get("neutral", {}),
        }
    except Exception as e:
        logger.exception("Multi-POV analysis failed")
        raise HTTPException(status_code=500, detail=str(e))
