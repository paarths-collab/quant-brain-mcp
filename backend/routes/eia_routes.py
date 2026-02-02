from fastapi import APIRouter, HTTPException
from backend.services.eia_service import EIAService

router = APIRouter(
    prefix="/api/eia",
    tags=["Energy Information"]
)

eia_service = EIAService()

@router.get("/reserves/oil")
async def get_oil_reserves():
    """
    Get Crude Oil Proved Reserves data.
    """
    data = eia_service.get_crude_oil_reserves()
    if "error" in data:
        raise HTTPException(status_code=500, detail=data["error"])
    return data

@router.get("/petroleum/summary")
async def get_petroleum_summary():
    """
    Get Weekly Petroleum Status Report summary.
    """
    data = eia_service.get_petroleum_summary()
    if "error" in data:
        raise HTTPException(status_code=500, detail=data["error"])
    return data
