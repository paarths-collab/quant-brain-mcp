"""
Treemap Routes - API endpoints for treemap visualization
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from backend.services.treemap_service import TreemapService


router = APIRouter(
    prefix="/api/treemap",
    tags=["Treemap"]
)

treemap_service = TreemapService()


@router.get("/indices")
async def get_indices(
    market: str = Query("india", description="Market: india or us")
):
    """
    Get all indices for a market without prices (fast).
    Use this for initial load.
    """
    try:
        indices = treemap_service.get_all_indices(market)
        return {
            "market": market,
            "count": len(indices),
            "indices": indices
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indices/live")
async def get_indices_with_prices(
    market: str = Query("india", description="Market: india or us")
):
    """
    Get all indices for a market WITH live prices from yfinance.
    This may take a few seconds.
    """
    try:
        indices = treemap_service.get_indices_with_prices(market)
        return {
            "market": market,
            "currency": "₹" if market.lower() == "india" else "$",
            "count": len(indices),
            "indices": indices
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/{index_id}")
async def get_index_stocks(
    index_id: str,
    market: str = Query("india", description="Market: india or us")
):
    """
    Get all constituent stocks of an index with live prices.
    Example: /api/treemap/index/nifty_50
    """
    try:
        data = treemap_service.get_index_constituents(index_id, market)
        if "error" in data:
            raise HTTPException(status_code=404, detail=data["error"])
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data")
async def get_treemap_data(
    market: str = Query("india", description="Market: india or us"),
    index_id: Optional[str] = Query(None, description="Index ID to drill down into")
):
    """
    Main treemap endpoint.
    - Without index_id: Returns all indices with prices
    - With index_id: Returns stocks for that index with prices
    
    Example:
    - /api/treemap/data?market=india (shows all indices)
    - /api/treemap/data?market=india&index_id=nifty_50 (shows NIFTY 50 stocks)
    """
    try:
        data = treemap_service.get_treemap_data(market, index_id)
        if "error" in data:
            raise HTTPException(status_code=404, detail=data["error"])
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gainers-losers/{index_id}")
async def get_gainers_losers(
    index_id: str,
    market: str = Query("india", description="Market: india or us"),
    top_n: int = Query(5, description="Number of top gainers/losers to return")
):
    """
    Get top gainers and losers for an index.
    Example: /api/treemap/gainers-losers/nifty_50?top_n=10
    """
    try:
        data = treemap_service.get_gainers_losers(index_id, market, top_n)
        if "error" in data:
            raise HTTPException(status_code=404, detail=data["error"])
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_stocks(
    q: str = Query(..., min_length=1, description="Search query"),
    market: str = Query("india", description="Market: india or us")
):
    """
    Search for stocks across all indices.
    Example: /api/treemap/search?q=reliance
    """
    try:
        results = treemap_service.search_stocks(q, market)
        return {
            "query": q,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors")
async def get_sectors(
    market: str = Query("india", description="Market: india or us")
):
    """
    Get all sectoral indices.
    Returns only indices of type "Sectoral".
    """
    try:
        all_indices = treemap_service.get_all_indices(market)
        sectors = [idx for idx in all_indices if idx["type"] == "Sectoral"]
        return {
            "market": market,
            "count": len(sectors),
            "sectors": sectors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/benchmarks")
async def get_benchmarks(
    market: str = Query("india", description="Market: india or us")
):
    """
    Get benchmark indices with live prices.
    Returns NIFTY 50, SENSEX, etc.
    """
    try:
        all_indices = treemap_service.get_indices_with_prices(market)
        benchmarks = [idx for idx in all_indices if idx["type"] == "Benchmark"]
        return {
            "market": market,
            "currency": "₹" if market.lower() == "india" else "$",
            "count": len(benchmarks),
            "benchmarks": benchmarks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{symbol}")
async def get_stock_details(
    symbol: str,
    market: str = Query("india", description="Market: india or us")
):
    """
    Get comprehensive stock details from yfinance.
    Returns all available information: price, valuation, financials, dividends, etc.
    
    Example: /api/treemap/stock/RELIANCE?market=india
    Example: /api/treemap/stock/AAPL?market=us
    """
    try:
        data = treemap_service.get_stock_details(symbol, market)
        if "error" in data and data.get("error"):
            raise HTTPException(status_code=404, detail=data["error"])
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
