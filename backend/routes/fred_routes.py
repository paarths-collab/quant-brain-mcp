"""
FRED Data Routes - API endpoints for FRED index data
"""
from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from backend.services.fred_data_service import FredDataService, ALL_DEFAULT_SERIES


router = APIRouter(
    prefix="/api/fred",
    tags=["FRED Data"]
)


# ============ Pydantic Models ============

class SyncRequest(BaseModel):
    series_id: str
    series_type: str = "index"
    days: int = 365


class BulkSyncRequest(BaseModel):
    days: int = 365


class SeriesResponse(BaseModel):
    series_id: str
    date: str
    value: Optional[float]


# ============ Helper Functions ============

def get_fred_service():
    """Dependency to get FRED service"""
    try:
        return FredDataService()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Sync Endpoints ============

@router.post("/sync/series")
async def sync_single_series(
    request: SyncRequest,
    service: FredDataService = Depends(get_fred_service)
):
    """Sync a single FRED series to database"""
    try:
        result = service.fetch_and_store_series(
            series_id=request.series_id,
            series_type=request.series_type,
            start_date=date.today() - timedelta(days=request.days),
            end_date=date.today()
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/indices")
async def sync_all_indices(
    request: BulkSyncRequest = BulkSyncRequest(),
    service: FredDataService = Depends(get_fred_service)
):
    """Sync all default index series (SP500, DJIA, NASDAQ100, etc.)"""
    try:
        results = service.sync_all_indices(days=request.days)
        return {
            "status": "completed",
            "series_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/rates")
async def sync_all_rates(
    request: BulkSyncRequest = BulkSyncRequest(),
    service: FredDataService = Depends(get_fred_service)
):
    """Sync all default interest rate series"""
    try:
        results = service.sync_all_rates(days=request.days)
        return {
            "status": "completed",
            "series_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all")
async def sync_all_series(
    request: BulkSyncRequest = BulkSyncRequest(),
    service: FredDataService = Depends(get_fred_service)
):
    """Sync all default FRED series (indices + rates)"""
    try:
        results = service.sync_all(days=request.days)
        return {
            "status": "completed",
            "indices_count": len(results.get("indices", [])),
            "rates_count": len(results.get("rates", [])),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Query Endpoints ============

@router.get("/series/{series_id}")
async def get_series_data(
    series_id: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: Optional[int] = Query(None, description="Limit number of records"),
    service: FredDataService = Depends(get_fred_service)
):
    """Get cached data for a specific FRED series"""
    try:
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
        
        data = service.get_cached_series(series_id, start, end)
        
        if limit:
            data = data[:limit]
        
        return {
            "series_id": series_id,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/series/{series_id}/latest")
async def get_series_latest(
    series_id: str,
    service: FredDataService = Depends(get_fred_service)
):
    """Get the latest value for a specific series"""
    try:
        data = service.get_cached_series(series_id, limit=1) # type: ignore
        if not data:
            raise HTTPException(status_code=404, detail=f"No data found for {series_id}")
        return data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_all_latest(
    series_ids: Optional[str] = Query(None, description="Comma-separated series IDs"),
    service: FredDataService = Depends(get_fred_service)
):
    """Get latest values for multiple series"""
    try:
        ids = series_ids.split(",") if series_ids else None
        data = service.get_cached_latest(ids)
        return {
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_index_dashboard(
    service: FredDataService = Depends(get_fred_service)
):
    """Get dashboard overview with all indices and rates"""
    try:
        return service.get_index_dashboard()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Metadata Endpoints ============

@router.get("/available-series")
async def get_available_series():
    """Get list of all available series that can be synced"""
    return {
        "total": len(ALL_DEFAULT_SERIES),
        "series": [
            {
                "series_id": k,
                "type": v["type"],
                "title": v["title"]
            }
            for k, v in ALL_DEFAULT_SERIES.items()
        ]
    }


# ============ Auto-fetch Endpoint ============

@router.get("/smart/{series_id}")
async def get_series_smart(
    series_id: str,
    max_age_hours: int = Query(24, description="Max age before refetch"),
    service: FredDataService = Depends(get_fred_service)
):
    """Get series data with automatic refresh if stale"""
    try:
        series_info = ALL_DEFAULT_SERIES.get(series_id, {"type": "index"})
        data = service.get_series_with_fallback(
            series_id,
            series_type=series_info["type"],
            max_age_hours=max_age_hours
        )
        return {
            "series_id": series_id,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
