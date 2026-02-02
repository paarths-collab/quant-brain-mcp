from fastapi import APIRouter, HTTPException
from backend.services.fundamentals_service import get_fundamentals_summary

router = APIRouter(prefix="/api/fundamentals", tags=["Fundamentals"])

@router.get("/summary/{symbol}")
def get_summary(symbol: str):
    """
    Returns aggregated fundamental data (Profile + Ratios + Growth).
    """
    try:
        data = get_fundamentals_summary(symbol)
        if not data or not data.get("name"):
             # Sometimes FMP returns empty if symbol invalid
            raise HTTPException(status_code=404, detail="Stock data not found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
