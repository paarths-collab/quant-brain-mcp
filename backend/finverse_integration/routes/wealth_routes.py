"""
FastAPI routes for the Finverse wealth pipeline (free implementation).
Compatibility layer that preserves the existing /api/wealth/analyze response shape.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict

from ..agents.wealth_orchestrator import WealthOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wealth", tags=["Wealth Management"])


class WealthAnalysisRequest(BaseModel):
    user_input: str = Field(..., description="Natural language description of financial situation")
    market: str = Field(default="US", description="Market (US, IN, etc.)")
    channel: str = Field(default="chat", description="chat, email, whatsapp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_input": "I want to invest $10,000 for 5 years with moderate risk.",
                "market": "US",
                "channel": "chat",
            }
        }
    )


class WealthAnalysisResponse(BaseModel):
    success: bool
    report: str
    profile: Optional[Dict[str, Any]] = None
    allocation: Optional[Dict[str, float]] = None
    selected_stock: Optional[Dict[str, Any]] = None
    stocks: Optional[List[Dict[str, Any]]] = None
    top_sectors: Optional[List[str]] = None
    selection_rationale: Optional[List[Dict[str, Any]]] = None
    rejection_rationale: Optional[List[Dict[str, Any]]] = None
    trade_plans: Optional[List[Dict[str, Any]]] = None
    news_context: Optional[Dict[str, Any]] = None
    selected_mf: Optional[Dict[str, Any]] = None
    selected_bonds: Optional[Dict[str, Any]] = None
    execution_log: List[str] = []
    errors: List[str] = []
    timestamp: str


_wealth_manager: Optional[WealthOrchestrator] = None


def sanitize_floats(obj: Any) -> Any:
    """
    Recursively walk a data structure and replace inf, -inf, and NaN
    with None, as they are not JSON compliant.
    """
    if isinstance(obj, dict):
        return {k: sanitize_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_floats(elem) for elem in obj]
    elif isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return None
        return obj
    return obj


def get_wealth_manager() -> WealthOrchestrator:
    global _wealth_manager
    if _wealth_manager is None:
        if not os.getenv("GROQ_API_KEY"):
            raise ValueError("GROQ_API_KEY is required for wealth analysis")
        _wealth_manager = WealthOrchestrator()
    return _wealth_manager


def map_wealth_state_to_response(state: Dict[str, Any]) -> Dict[str, Any]:
    allocation = state.get("allocation_strategy", {}) or {}
    selected_stocks = state.get("selected_stocks") or []
    primary_stock = state.get("selected_stock") or (selected_stocks[0] if selected_stocks else None)
    errors = state.get("errors", []) or []

    return sanitize_floats({
        "success": not errors,
        "report": state.get("investment_report", ""),
        "profile": state.get("user_profile"),
        "allocation": allocation,
        "selected_stock": primary_stock,
        "stocks": selected_stocks,
        "top_sectors": state.get("top_sectors", []) or [],
        "selection_rationale": state.get("selection_rationale", []) or [],
        "rejection_rationale": state.get("rejection_rationale", []) or [],
        "trade_plans": state.get("trade_plans", []) or [],
        "news_context": state.get("news_context", {}) or {},
        "selected_mf": None,
        "selected_bonds": None,
        "execution_log": state.get("execution_log", []) or [],
        "errors": errors,
        "timestamp": datetime.now().isoformat(),
    })


@router.post("/analyze", response_model=WealthAnalysisResponse)
async def analyze_wealth(request: WealthAnalysisRequest):
    try:
        manager = get_wealth_manager()
        timeout_sec = float(os.getenv("WEALTH_TIMEOUT_SEC", "240"))
        result = await asyncio.wait_for(
            manager.run_workflow(
                user_input=request.user_input,
                market=request.market,
                channel=request.channel,
            ),
            timeout=timeout_sec,
        )
        return WealthAnalysisResponse(**map_wealth_state_to_response(result))
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Analysis took too long. Please try again later.",
        )
    except Exception as e:
        logger.exception("Wealth analysis failed")
        raise HTTPException(status_code=500, detail=f"Wealth analysis failed: {str(e)}")


@router.get("/analyze/stream")
async def analyze_wealth_stream(user_input: str, market: str = "US", channel: str = "chat"):
    async def event_generator():
        try:
            manager = get_wealth_manager()
            yield f"data: {json.dumps({'stage': 'start', 'message': 'Starting analysis'})}\n\n"
            result = await manager.run_workflow(user_input=user_input, market=market, channel=channel)
            payload = map_wealth_state_to_response(result)
            yield f"data: {json.dumps({'stage': 'complete', 'data': payload})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'stage': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
