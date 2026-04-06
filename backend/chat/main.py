import logging
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import List, Dict, Any, Optional

# Existing routers to merge
from .super_agent import router as super_agent_router
from .stock_advisor import router as stock_advisor_router
from .sentiment import router as sentiment_router
from .research_legacy import router as research_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["AI Chat & Research"])

# Mounting legacy sub-routers for now to keep it clean, but grouping them in this module's main.py
router.include_router(super_agent_router)
router.include_router(stock_advisor_router)
router.include_router(sentiment_router)
router.include_router(research_router)

# Example of a new, unified endpoint if needed later
@router.get("/status")
def get_chat_status():
    return {"status": "AI modules fully operational"}
