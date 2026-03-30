import math
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from backend.database.connection import get_db

# Import consolidated services
from .service import sectors_service
from .intel_service import (
    refresh_sector,
    refresh_all_sectors,
    list_latest_snapshots,
    recommend_sectors_for_user,
    get_sector_constituents,
    get_markets
)
# Localized services (Redundant Isolation)
from .core.fundamentals_service import get_fundamentals_summary
from .core.market_data_service import calculate_indicators
from .core.stock_sentiment_service import fetch_duckduckgo_news
from .core.sector_service import fetch_sector_performance

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Sectors & Treemaps"])

def _sanitize_for_json(value):
    """Recursively replace non-finite floats with None for JSON compliance."""
    if hasattr(value, "item"):
        try: value = value.item()
        except: pass
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(v) for v in value]
    return str(value)

def _snapshot_to_dict(snapshot):
    return {
        "id": snapshot.id,
        "sector": snapshot.sector,
        "market": snapshot.market,
        "as_of": snapshot.as_of.isoformat() if snapshot.as_of else None,
        "news_item_ids": snapshot.news_item_ids,
        "sector_summary": snapshot.sector_summary,
        "momentum": snapshot.momentum,
        "risk_notes": snapshot.risk_notes,
        "who_should_invest": snapshot.who_should_invest,
        "suitable_profiles": snapshot.suitable_profiles,
        "top_stocks": snapshot.top_stocks,
        "score": snapshot.score,
        "llm_model": snapshot.llm_model,
    }

# --- Legacy /api/treemap routes ---

@router.get("/treemap/indices")
async def get_indices(market: str = Query("india")):
    indices = sectors_service._get_market_indices(market) # Use the fast list
    return _sanitize_for_json({"market": market, "count": len(indices), "indices": indices})

@router.get("/treemap/indices/live")
async def get_indices_live(market: str = Query("india")):
    try:
        indices = sectors_service.get_indices_live(market)
        return _sanitize_for_json({"market": market, "count": len(indices), "indices": indices})
    except Exception as e:
        logger.error(f"Treemap live error: {e}")
        return {"error": str(e), "indices": []}

@router.get("/treemap/index/{index_id}")
async def get_index_stocks(
    index_id: str, 
    market: str = Query("india"), 
    include_prices: bool = Query(True)
):
    data = sectors_service.get_index_constituents(index_id, market, include_prices)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return _sanitize_for_json(data)

# --- Legacy /api/sectors routes ---

@router.get("/sectors/performance")
def get_sector_performance():
    data = fetch_sector_performance()
    return {"name": "Market", "children": data}

# --- Legacy /api/sector-intel routes ---

@router.get("/sector-intel/latest")
def get_intel_latest(market: str = Query(None), sector: str = Query(None), db=Depends(get_db)):
    if sector:
        snapshots = [s for s in list_latest_snapshots(db, market) if s.sector.lower() == sector.lower()]
        if not snapshots: raise HTTPException(status_code=404, detail="Not found")
        return _snapshot_to_dict(snapshots[0])
    snapshots = list_latest_snapshots(db, market)
    return [_snapshot_to_dict(s) for s in snapshots]

@router.post("/sector-intel/refresh")
def refresh_intel(payload: dict = Body(...), db=Depends(get_db)):
    market = (payload.get("market") or "").upper() or None
    sector = payload.get("sector")
    force = bool(payload.get("force", False))
    if sector and market:
        res = refresh_sector(db, sector, market, force=force)
        db.commit()
        return res
    res = refresh_all_sectors(db, markets=[market] if market else None, force=force)
    db.commit()
    return res

@router.post("/sector-intel/recommend")
def recommend_intel(payload: dict = Body(...), db=Depends(get_db)):
    return recommend_sectors_for_user(
        db, 
        market=payload.get("market", "US").upper(),
        risk_score=payload.get("risk_score"),
        limit=int(payload.get("limit", 5))
    )

@router.get("/sector-intel/sector/{sector}/stocks")
def sector_intel_stocks(
    sector: str,
    market: str = Query("US"),
    limit: int = Query(10),
    include_fundamentals: bool = Query(True),
    include_technicals: bool = Query(True),
):
    market_code = market.upper()
    stocks = get_sector_constituents(market_code, sector, limit=limit)
    enriched = []
    for stock in stocks:
        sym = stock["symbol"]
        item = {**stock, "market": market_code}
        if include_fundamentals: item["fundamentals"] = get_fundamentals_summary(sym)
        if include_technicals: 
             indicators = calculate_indicators(sym, range="6mo", interval="1d")
             item["technicals"] = {"rsi": indicators.get("rsi")[-1] if indicators.get("rsi") else None}
        enriched.append(item)
    return {"sector": sector, "market": market_code, "stocks": enriched}
