import logging
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import List, Dict, Any, Optional

# Existing routers to merge
# Localized services (Redundant Isolation)
from .investor_profile import router as investor_profile_router
from .long_term import router as long_term_router
from .reports import router as reports_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Portfolio & Wealth"])

# Grouping all portfolio-related routes into one module
router.include_router(investor_profile_router)
router.include_router(long_term_router)
router.include_router(reports_router)

@router.get("/portfolio/overview")
def get_portfolio_overview():
    return {"status": "Portfolio and wealth management services are active"}
