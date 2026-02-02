from fastapi import APIRouter, HTTPException, Body
from backend.services.research_service import generate_research_report
from typing import Dict, Any

router = APIRouter(prefix="/api/research", tags=["Research Agent"])

@router.post("/analyze")
def analyze_stock(
    payload: Dict[str, str] = Body(...)
):
    """
    Generates an AI Research Report for a consolidated symbol.
    Payload: {"symbol": "AAPL"}
    """
    symbol = payload.get("symbol")
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
        
    try:
        report = generate_research_report(symbol)
        if "error" in report:
             raise HTTPException(status_code=400, detail=report["error"])
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
