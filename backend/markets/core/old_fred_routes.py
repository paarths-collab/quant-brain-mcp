"""
FRED Data Routes - API endpoints for FRED index data
"""
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel

from backend.services.fred_data_service import FredDataService, ALL_DEFAULT_SERIES
from backend.database.connection import get_db_session
from backend.database.models import FredData


router = APIRouter(
    prefix="/api/fred",
    tags=["FRED Data"]
)

GOLD_SERIES_IDS = {"GOLDAMGBD228NLBM"}


def _fetch_gold_price_from_yf(max_age_hours: int = 12) -> Optional[Dict[str, Any]]:
    cache_path = Path(__file__).resolve().parents[1] / "cache" / "gold_price.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            cached_at = payload.get("cached_at")
            if cached_at:
                cached_dt = datetime.fromisoformat(cached_at)
                if datetime.utcnow() - cached_dt < timedelta(hours=max_age_hours):
                    return payload.get("payload")
        except Exception:
            pass

    try:
        import yfinance as yf
    except Exception:
        return None

    try:
        symbols = ["XAUUSD=X", "GC=F", "GOLD"]
        price = None
        prev = None
        used_symbol = None
        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                continue
            closes = hist["Close"].dropna()
            if closes.empty:
                continue
            last = closes.iloc[-1]
            prev_close = closes.iloc[-2] if len(closes) > 1 else None
            if last is not None and last > 0:
                price = float(last)
                prev = float(prev_close) if prev_close is not None else None
                used_symbol = symbol
                break
        if price is None:
            return None

        change = (price - prev) if (price is not None and prev is not None) else None
        change_pct = (change / prev * 100) if (change is not None and prev not in (None, 0)) else None

        payload = {
            "value": price,
            "previous": prev,
            "change": change,
            "change_pct": change_pct,
            "date": date.today().isoformat(),
            "symbol": used_symbol,
            "status": "success",
        }
        cache_path.write_text(
            json.dumps({"cached_at": datetime.utcnow().isoformat(), "payload": payload}),
            encoding="utf-8",
        )
        return payload
    except Exception:
        return None


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


@router.get("/latest-live")
async def get_latest_live(
    series_ids: Optional[str] = Query(None, description="Comma-separated series IDs"),
    service: FredDataService = Depends(get_fred_service)
):
    """Fetch latest values directly from FRED (no cache)."""
    try:
        ids = series_ids.split(",") if series_ids else list(ALL_DEFAULT_SERIES.keys())
        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        data: Dict[str, Dict] = {}

        for series_id in ids:
            series = service.fetch_series(series_id, start_date, end_date)
            series = series.dropna()
            if series.empty:
                data[series_id] = {
                    "series_id": series_id,
                    "status": "error",
                    "message": "No data returned",
                }
                continue

            latest_value = float(series.iloc[-1])
            latest_date = series.index[-1].strftime("%Y-%m-%d")
            prev_value = float(series.iloc[-2]) if len(series) > 1 else None
            change = latest_value - prev_value if prev_value is not None else None
            change_pct = (change / prev_value * 100) if prev_value not in (None, 0) else None

            meta = ALL_DEFAULT_SERIES.get(series_id, {"title": series_id, "type": "index"})
            data[series_id] = {
                "series_id": series_id,
                "title": meta.get("title", series_id),
                "type": meta.get("type", "index"),
                "value": latest_value,
                "date": latest_date,
                "previous": prev_value,
                "change": change,
                "change_pct": change_pct,
                "status": "success",
            }

        return {
            "count": len(data),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest-cached")
async def get_latest_cached(
    series_ids: Optional[str] = Query(None, description="Comma-separated series IDs"),
    max_age_hours: int = Query(24, description="Max age before refresh"),
    service: FredDataService = Depends(get_fred_service)
):
    """Get latest values from cache, refresh only if stale/missing."""
    try:
        ids = series_ids.split(",") if series_ids else list(ALL_DEFAULT_SERIES.keys())
        data: Dict[str, Dict] = {}

        with get_db_session() as db:
            repo = service  # keep naming consistent
            for series_id in ids:
                try:
                    latest = db.query(FredData).filter(FredData.series_id == series_id).order_by(FredData.date.desc()).first()
                    needs_refresh = True
                    if latest and latest.updated_at:
                        age = datetime.utcnow() - latest.updated_at.replace(tzinfo=None)
                        needs_refresh = age > timedelta(hours=max_age_hours)

                    if latest is None or needs_refresh:
                        series_info = ALL_DEFAULT_SERIES.get(series_id, {"type": "index"})
                        service.fetch_and_store_series(series_id, series_info["type"], start_date=date.today() - timedelta(days=365), end_date=date.today())

                    rows = (
                        db.query(FredData)
                        .filter(FredData.series_id == series_id)
                        .order_by(FredData.date.desc())
                        .limit(2)
                        .all()
                    )

                    if not rows:
                        if series_id in GOLD_SERIES_IDS:
                            gold_payload = _fetch_gold_price_from_yf(max_age_hours=max_age_hours)
                            if gold_payload:
                                data[series_id] = {
                                    "series_id": series_id,
                                    "title": "Gold Price (Yahoo Finance)",
                                    "type": "commodity",
                                    "value": gold_payload.get("value"),
                                    "date": gold_payload.get("date"),
                                    "previous": gold_payload.get("previous"),
                                    "change": gold_payload.get("change"),
                                    "change_pct": gold_payload.get("change_pct"),
                                    "status": "success",
                                    "updated_at": None,
                                    "source": "yfinance",
                                }
                                continue
                        data[series_id] = {
                            "series_id": series_id,
                            "status": "error",
                            "message": "Gold price unavailable from Yahoo Finance" if series_id in GOLD_SERIES_IDS else "No cached data",
                        }
                        continue

                    latest_row = rows[0]
                    prev_row = rows[1] if len(rows) > 1 else None
                    latest_value = latest_row.value
                    prev_value = prev_row.value if prev_row else None
                    change = (latest_value - prev_value) if (latest_value is not None and prev_value is not None) else None
                    change_pct = (change / prev_value * 100) if (change is not None and prev_value not in (None, 0)) else None

                    meta = ALL_DEFAULT_SERIES.get(series_id, {"title": series_id, "type": "index"})
                    if series_id in GOLD_SERIES_IDS and latest_value is None:
                        gold_payload = _fetch_gold_price_from_yf(max_age_hours=max_age_hours)
                        if gold_payload:
                            data[series_id] = {
                                "series_id": series_id,
                                "title": "Gold Price (Yahoo Finance)",
                                "type": "commodity",
                                "value": gold_payload.get("value"),
                                "date": gold_payload.get("date"),
                                "previous": gold_payload.get("previous"),
                                "change": gold_payload.get("change"),
                                "change_pct": gold_payload.get("change_pct"),
                                "status": "success",
                                "updated_at": None,
                                "source": "yfinance",
                            }
                            continue

                    data[series_id] = {
                        "series_id": series_id,
                        "title": meta.get("title", series_id),
                        "type": meta.get("type", "index"),
                        "value": latest_value,
                        "date": latest_row.date.isoformat(),
                        "previous": prev_value,
                        "change": change,
                        "change_pct": change_pct,
                        "status": "success",
                        "updated_at": latest_row.updated_at.isoformat() if latest_row.updated_at else None,
                    }
                except Exception as e:
                    data[series_id] = {
                        "series_id": series_id,
                        "status": "error",
                        "message": str(e),
                    }

        return {
            "count": len(data),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending-news")
async def get_trending_news(
    series_ids: Optional[str] = Query(None, description="Comma-separated series IDs (optional)"),
    max_age_hours: int = Query(12, description="Max age before refresh"),
    limit: int = Query(6, description="Max articles to return")
):
    """Fetch DuckDuckGo news for the most volatile index."""
    try:
        # NewsService handles availability checks


        ids = series_ids.split(",") if series_ids else [
            k for k, v in ALL_DEFAULT_SERIES.items() if v.get("type") == "index"
        ]

        cache_path = Path(__file__).resolve().parents[1] / "cache" / "fred_trending_news.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cached_payload = None
        if cache_path.exists():
            try:
                cached_payload = json.loads(cache_path.read_text(encoding="utf-8"))
                cached_at = cached_payload.get("cached_at")
                if cached_at:
                    cached_dt = datetime.fromisoformat(cached_at)
                    age = datetime.utcnow() - cached_dt
                    if age < timedelta(hours=max_age_hours):
                        payload = cached_payload.get("payload") or {}
                        payload["cached"] = True
                        payload["cached_at"] = cached_at
                        return payload
            except Exception:
                cached_payload = None

        trending = None
        service = FredDataService()
        with get_db_session() as db:
            for series_id in ids:
                latest = (
                    db.query(FredData)
                    .filter(FredData.series_id == series_id)
                    .order_by(FredData.date.desc())
                    .first()
                )

                needs_refresh = True
                if latest and latest.updated_at:
                    age = datetime.utcnow() - latest.updated_at.replace(tzinfo=None)
                    needs_refresh = age > timedelta(hours=max_age_hours)

                if latest is None or needs_refresh:
                    series_info = ALL_DEFAULT_SERIES.get(series_id, {"type": "index"})
                    service.fetch_and_store_series(
                        series_id,
                        series_info["type"],
                        start_date=date.today() - timedelta(days=365),
                        end_date=date.today(),
                    )

                rows = (
                    db.query(FredData)
                    .filter(FredData.series_id == series_id)
                    .order_by(FredData.date.desc())
                    .limit(2)
                    .all()
                )
                if not rows:
                    continue

                latest_row = rows[0]
                prev_row = rows[1] if len(rows) > 1 else None
                latest_value = latest_row.value
                prev_value = prev_row.value if prev_row else None
                change_pct = (
                    ((latest_value - prev_value) / prev_value) * 100
                    if (latest_value is not None and prev_value not in (None, 0))
                    else None
                )

                if change_pct is None:
                    continue

                score = abs(change_pct)
                if trending is None or score > trending["score"]:
                    meta = ALL_DEFAULT_SERIES.get(series_id, {"title": series_id})
                    trending = {
                        "series_id": series_id,
                        "title": meta.get("title", series_id),
                        "date": latest_row.date.isoformat(),
                        "value": latest_value,
                        "change_pct": change_pct,
                        "score": score,
                    }

        if not trending:
            return {
                "status": "error",
                "message": "No cached data to determine trending index.",
                "articles": [],
            }

        from backend.services.news_service import news_service
        
        query = f"{trending['title']} index news"
        
        try:
            # Use centralized news service
            results = news_service.get_news(query, limit)
            
            articles = []
            for item in results:
                articles.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "source": item.get("source"),
                    "date": item.get("date"),
                    "summary": item.get("body"),
                })
        except Exception as e:
            if cached_payload:
                payload = cached_payload.get("payload") or {}
                payload["cached"] = True
                payload["cached_at"] = cached_payload.get("cached_at")
                payload["status"] = "stale"
                payload["message"] = f"News fetch failed; serving cached results. ({e})"
                return payload
            raise

        payload = {
            "status": "success",
            "trending": trending,
            "query": query,
            "articles": articles,
        }
        cache_path.write_text(
            json.dumps({"cached_at": datetime.utcnow().isoformat(), "payload": payload}),
            encoding="utf-8"
        )
        payload["cached"] = False
        payload["cached_at"] = datetime.utcnow().isoformat()
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index-news")
async def get_index_news(
    series_ids: Optional[str] = Query(None, description="Comma-separated series IDs (optional)"),
    max_age_hours: int = Query(12, description="Max age before refresh"),
    limit: int = Query(5, description="Max articles per index"),
    refresh: bool = Query(False, description="Force refresh instead of using cache"),
    background_tasks: BackgroundTasks = None
):
    """Fetch DuckDuckGo news for each index."""
    try:
        # NewsService handles availability checks


        ids = series_ids.split(",") if series_ids else [
            k for k, v in ALL_DEFAULT_SERIES.items() if v.get("type") == "index"
        ]

        cache_dir = Path(__file__).resolve().parents[1] / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        def load_cache(path: Path):
            if not path.exists():
                return None
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                cached_at = payload.get("cached_at")
                if cached_at:
                    cached_dt = datetime.fromisoformat(cached_at)
                    age = datetime.utcnow() - cached_dt
                    if age < timedelta(hours=max_age_hours):
                        data = payload.get("payload") or {}
                        data["cached"] = True
                        data["cached_at"] = cached_at
                        return data
            except Exception:
                return None
            return None

        def fetch_and_cache(title: str, query: str, cache_path: Path):
            from backend.services.news_service import news_service
            results = news_service.get_news(query, limit)
            articles = []
            for item in results:
                articles.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "source": item.get("source"),
                    "date": item.get("date"),
                    "summary": item.get("body"),
                })
            payload = {
                "status": "success",
                "title": title,
                "query": query,
                "articles": articles,
            }
            cache_path.write_text(
                json.dumps({"cached_at": datetime.utcnow().isoformat(), "payload": payload}),
                encoding="utf-8"
            )

        results: Dict[str, Dict] = {}

        for series_id in ids:
            meta = ALL_DEFAULT_SERIES.get(series_id, {"title": series_id})
            title = meta.get("title", series_id)
            cache_path = cache_dir / f"fred_index_news_{series_id}.json"

            cached = load_cache(cache_path)
            if cached and not refresh:
                results[series_id] = cached
                continue

            try:
                query = f"{title} index news"
                from backend.services.news_service import news_service
                
                # Use centralized news service
                results = news_service.get_news(query, limit)
                
                articles = []
                for item in results:
                    articles.append({
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "source": item.get("source"),
                        "date": item.get("date"),
                        "summary": item.get("body"),
                    })
                    payload = {
                        "status": "success",
                        "title": title,
                        "query": query,
                        "articles": articles,
                    }
                    cache_path.write_text(
                        json.dumps({"cached_at": datetime.utcnow().isoformat(), "payload": payload}),
                        encoding="utf-8"
                    )
                    payload["cached"] = False
                    payload["cached_at"] = datetime.utcnow().isoformat()
                    results[series_id] = payload
                else:
                    results[series_id] = {
                        "status": "warming",
                        "title": title,
                        "query": query,
                        "articles": [],
                    }
                    if background_tasks is not None:
                        background_tasks.add_task(fetch_and_cache, title, query, cache_path)
            except Exception as e:
                cached_any = None
                if cache_path.exists():
                    try:
                        cached_any = json.loads(cache_path.read_text(encoding="utf-8"))
                    except Exception:
                        cached_any = None
                if cached_any:
                    payload = cached_any.get("payload") or {}
                    payload["cached"] = True
                    payload["cached_at"] = cached_any.get("cached_at")
                    payload["status"] = "stale"
                    payload["message"] = f"News fetch failed; serving cached results. ({e})"
                    results[series_id] = payload
                else:
                    results[series_id] = {
                        "status": "error",
                        "message": str(e),
                        "title": title,
                        "query": query,
                        "articles": [],
                    }

        return {
            "status": "success",
            "count": len(results),
            "data": results,
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
