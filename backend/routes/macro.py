from fastapi import APIRouter, HTTPException
from backend.services.macro_service import fetch_macro_prices, get_geo_data

router = APIRouter(prefix="/api/macro", tags=["Macro"])

@router.get("/prices")
def get_prices():
    """
    Returns live prices for Bonds, Oil, Gold, etc.
    """
    try:
        data = fetch_macro_prices()
        return {"items": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/globe/{commodity_type}")
def get_globe_data(commodity_type: str):
    """
    Returns GeoJSON-like points for 'oil', 'gold', etc.
    """
    data = get_geo_data(commodity_type)
    if not data:
        raise HTTPException(status_code=404, detail=f"No geo data for {commodity_type}")
    return {"commodity": commodity_type, "locations": data}
