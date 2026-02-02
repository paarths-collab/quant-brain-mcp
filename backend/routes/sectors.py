from fastapi import APIRouter, HTTPException
from backend.services.sector_service import fetch_sector_performance

router = APIRouter(prefix="/api/sectors", tags=["Sectors"])

@router.get("/performance")
def get_sector_performance():
    """
    Returns hierarchical sector performance data for Treemaps.
    """
    try:
        data = fetch_sector_performance()
        if not data:
            raise HTTPException(status_code=404, detail="Sector data unavailable")
        return {"name": "Market", "children": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
