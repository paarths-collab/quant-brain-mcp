import math
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from backend.database.connection import get_db

# Unified services
from .service import sectors_service
from backend.services.technical_analysis import technical_service

# Sector Intel services
from .intel_service import (
    refresh_sector,
    refresh_all_sectors,
    list_latest_snapshots,
    recommend_sectors_for_user,
    get_sector_constituents,
    get_markets
)

# Localized services (To be retired)
from .core.fundamentals_service import get_fundamentals_summary
from .core.stock_sentiment_service import fetch_duckduckgo_news
from .core.sector_service import fetch_sector_performance

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Sectors & Treemaps"])

def _sanitize_for_json(value):
    """Recursively replace non-finite floats with None for JSON compliance."""
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception as exc:
            logger.debug("Failed to coerce scalar value %r: %s", value, exc)
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
    try:
        indices = sectors_service._get_market_indices(market) # Use the fast list
        return _sanitize_for_json({"market": market, "count": len(indices), "indices": indices})
    except Exception as e:
        logger.error(f"Treemap indices error for market={market}: {e}")
        return {"market": market, "count": 0, "indices": [], "error": "indices_unavailable"}

@router.get("/treemap/indices/live")
async def get_indices_live(market: str = Query("india")):
    try:
        indices = sectors_service.get_indices_live(market)
        return _sanitize_for_json({"market": market, "count": len(indices), "indices": indices})
    except Exception as e:
        logger.error(f"Treemap live error: {e}")
        return {"market": market, "count": 0, "indices": [], "error": str(e)}

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
    
@router.get("/{index_id}")
async def get_index_stocks_alias(
    index_id: str, 
    market: str = Query("india"), 
    include_prices: bool = Query(True)
):
    """Compatibility alias for /api/sectors/{index_id}"""
    return await get_index_stocks(index_id, market, include_prices)

@router.get("/treemap/stock/{symbol}")
def get_treemap_stock(symbol: str, market: str = Query("india")):
    from backend.services.market_data import market_service
    q_key = market_service.normalize_ticker(symbol, market)
    
    # 1. Fetch live quotes for latest price
    quotes = market_service.fetch_multiple_quotes([q_key])
    q = quotes.get(q_key, {})
    
    # 2. Fetch comprehensive info for fundamentals
    info = market_service.get_fundamentals(q_key)
    if not isinstance(info, dict):
        info = {}

    return _sanitize_for_json({
        "symbol": symbol,
        "name": info.get("shortName") or info.get("longName") or symbol,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "price": {
            "current": q.get("price") or info.get("currentPrice") or info.get("regularMarketPrice"),
            "change": q.get("change") or 0.0,
            "change_percent": q.get("change_percent") or 0.0,
            "open": info.get("open"),
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low": info.get("fiftyTwoWeekLow"),
        },
        "valuation": {
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "enterprise_value": info.get("enterpriseValue"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
        },
        "financials": {
            "revenue": info.get("totalRevenue"),
            "eps_trailing": info.get("trailingEps"),
            "net_income": info.get("netIncomeToCommon"),
            "profit_margin": info.get("profitMargins"),
            "return_on_equity": info.get("returnOnEquity"),
        },
        "dividends": {
            "dividend_yield": info.get("dividendYield"),
        },
        "volume": {
            "current": info.get("volume"),
            "avg_3m": info.get("averageVolume"),
        },
        "trading": {
            "beta": info.get("beta"),
        },
        "balance_sheet": {
            "total_debt": info.get("totalDebt"),
        },
        "analyst": {
            "recommendation": info.get("recommendationKey"),
            "target_mean": info.get("targetMeanPrice"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
        },
        "company": {
            "description": info.get("longBusinessSummary"),
            "website": info.get("website"),
            "employees": info.get("fullTimeEmployees"),
            "country": info.get("country"),
        }
    })

# --- Performance and Treemap routes ---

@router.get("/performance")
def get_sector_performance():
    data = fetch_sector_performance()
    return {"name": "Market", "children": data}

# --- Legacy /api/sector-intel routes ---

@router.get("/intel/latest")
def get_intel_latest(market: str = Query(None), sector: str = Query(None), db=Depends(get_db)):
    if sector:
        snapshots = [s for s in list_latest_snapshots(db, market) if s.sector.lower() == sector.lower()]
        if not snapshots: raise HTTPException(status_code=404, detail="Not found")
        return _snapshot_to_dict(snapshots[0])
    snapshots = list_latest_snapshots(db, market)
    return [_snapshot_to_dict(s) for s in snapshots]

@router.post("/intel/refresh")
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

@router.post("/intel/recommend")
def recommend_intel(payload: dict = Body(...), db=Depends(get_db)):
    return recommend_sectors_for_user(
        db, 
        market=payload.get("market", "US").upper(),
        risk_score=payload.get("risk_score"),
        limit=int(payload.get("limit", 5))
    )

@router.get("/intel/stocks/{sector}")
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
        if include_technicals: 
             # Use the NEW unified TechnicalAnalysisService
             indicators = technical_service.calculate_indicators(sym, range_period="6mo", interval="1d", market=market_code)
             rsi_list = indicators.get("rsi")
             item["technicals"] = {"rsi": rsi_list[-1] if rsi_list else None}
        enriched.append(item)
    return {"sector": sector, "market": market_code, "stocks": enriched}
