from fastapi import APIRouter, HTTPException, Query, Body, Depends

from backend.database.connection import get_db
from backend.services.sector_intel_service import (
    refresh_sector,
    refresh_all_sectors,
    list_latest_snapshots,
    recommend_sectors_for_user,
    get_sector_constituents,
    get_markets,
)
from backend.services.fundamentals_service import get_fundamentals_summary
from backend.services.market_data_service import calculate_indicators
from backend.services.stock_sentiment_service import fetch_duckduckgo_news


router = APIRouter(prefix="/api/sector-intel", tags=["Sector Intelligence"])


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


@router.get("/latest")
def get_latest(
    market: str = Query(None),
    sector: str = Query(None),
    db=Depends(get_db),
):
    """
    Returns latest sector snapshots.
    """
    try:
        if sector:
            snapshots = [snapshot for snapshot in list_latest_snapshots(db, market) if snapshot.sector.lower() == sector.lower()]
            if not snapshots:
                raise HTTPException(status_code=404, detail="Sector snapshot not found")
            return _snapshot_to_dict(snapshots[0])

        snapshots = list_latest_snapshots(db, market)
        return [_snapshot_to_dict(snapshot) for snapshot in snapshots]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
def refresh(
    payload: dict = Body(default_factory=dict),
    db=Depends(get_db),
):
    """
    Refresh sector snapshots (all or specific sector).
    """
    try:
        market = (payload.get("market") or "").upper() or None
        sector = payload.get("sector")
        force = bool(payload.get("force", False))

        if sector and market:
            res = refresh_sector(db, sector, market, force=force)
            db.commit()
            return res
        if sector and not market:
            results = []
            for m in get_markets():
                results.append(refresh_sector(db, sector, m, force=force))
            db.commit()
            return {"status": "ok", "results": results}

        res = refresh_all_sectors(db, markets=[market] if market else None, force=force)
        db.commit()
        return res
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend")
def recommend(
    payload: dict = Body(default_factory=dict),
    db=Depends(get_db),
):
    """
    Recommend sectors for a given user profile using cached snapshots.
    """
    try:
        market = (payload.get("market") or "US").upper()
        risk_score = payload.get("risk_score")
        risk_tolerance = payload.get("risk_tolerance")
        time_horizon_years = payload.get("time_horizon_years")
        goal = payload.get("goal")
        limit = int(payload.get("limit", 5))
        return recommend_sectors_for_user(
            db,
            market=market,
            risk_score=risk_score,
            risk_tolerance=risk_tolerance,
            time_horizon_years=time_horizon_years,
            goal=goal,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sector/{sector}/stocks")
def sector_stocks(
    sector: str,
    market: str = Query("US"),
    limit: int = Query(10),
    include_fundamentals: bool = Query(True),
    include_technicals: bool = Query(False),
    include_news: bool = Query(True),
):
    """
    Return sector constituents with optional fundamentals, technicals, and news.
    """
    try:
        def _last(values):
            return values[-1] if isinstance(values, list) and values else None

        market_code = (market or "US").upper()
        stocks = get_sector_constituents(market_code, sector, limit=limit)
        enriched = []

        for stock in stocks:
            symbol = stock.get("symbol")
            name = stock.get("name")
            payload = {"symbol": symbol, "name": name, "sector": sector, "market": market_code}

            if include_fundamentals:
                payload["fundamentals"] = get_fundamentals_summary(symbol)

            if include_technicals:
                indicators = calculate_indicators(symbol, range="6mo", interval="1d")
                latest = {}
                if indicators and indicators.get("dates"):
                    latest = {
                        "date": _last(indicators.get("dates")),
                        "rsi": _last(indicators.get("rsi")),
                        "macd": {
                            "line": _last(indicators.get("macd", {}).get("line")),
                            "signal": _last(indicators.get("macd", {}).get("signal")),
                            "histogram": _last(indicators.get("macd", {}).get("histogram")),
                        },
                        "ema": {
                            "20": _last(indicators.get("ema", {}).get("20")),
                            "50": _last(indicators.get("ema", {}).get("50")),
                            "200": _last(indicators.get("ema", {}).get("200")),
                        },
                        "atr": _last(indicators.get("atr")),
                        "vwap": _last(indicators.get("vwap")),
                    }
                payload["technicals"] = latest

            if include_news:
                payload["news"] = fetch_duckduckgo_news(name or "", symbol, limit=6)

            enriched.append(payload)

        return {"sector": sector, "market": market_code, "stocks": enriched}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
