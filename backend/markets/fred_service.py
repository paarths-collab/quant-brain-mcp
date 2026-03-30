import os
import json
import logging
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from fredapi import Fred

from backend.database.connection import get_db_session
from backend.database.fred_repository import FredRepository

logger = logging.getLogger(__name__)

def _fetch_gold_price_from_yf(max_age_hours: int = 12) -> Optional[Dict[str, Any]]:
    cache_path = Path(__file__).resolve().parents[2] / "cache" / "gold_price.json"
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
        symbols = ["XAUUSD=X", "GC=F", "GOLD"]
        price = None
        prev = None
        used_symbol = None
        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty: continue
            closes = hist["Close"].dropna()
            if closes.empty: continue
            last = closes.iloc[-1]
            prev_close = closes.iloc[-2] if len(closes) > 1 else None
            if last is not None and last > 0:
                price = float(last)
                prev = float(prev_close) if prev_close is not None else None
                used_symbol = symbol
                break
        
        if price is None: return None
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
            json.dumps({"cached_at": datetime.utcnow().isoformat(), "payload": payload}, indent=2),
            encoding="utf-8",
        )
        return payload
    except Exception:
        return None

# Default FRED series for common indices
ALL_DEFAULT_SERIES = {
    'SP500': {'type': 'index', 'title': 'S&P 500'},
    'DJIA': {'type': 'index', 'title': 'Dow Jones Industrial Average'},
    'NASDAQ100': {'type': 'index', 'title': 'NASDAQ 100'},
    'VIXCLS': {'type': 'index', 'title': 'VIX Volatility Index'},
    'DGS10': {'type': 'rate', 'title': '10-Year Treasury Rate'},
    'CPIAUCSL': {'type': 'economic', 'title': 'Consumer Price Index'},
    'UNRATE': {'type': 'economic', 'title': 'Unemployment Rate'},
    'GDP': {'type': 'economic', 'title': 'Gross Domestic Product'},
    'GOLDAMGBD228NLBM': {'type': 'commodity', 'title': 'Gold Price (AM)'},
}

class FredDataService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        if not self.api_key:
            raise ValueError("FRED_API_KEY not found in environment")
        self.fred = Fred(api_key=self.api_key)
    
    def fetch_series(self, series_id: str, start_date=None, end_date=None) -> pd.Series:
        try:
            return self.fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
        except:
            return pd.Series()

    def get_all_series_metadata(self) -> List[Dict]:
        return [{"id": k, **v} for k, v in ALL_DEFAULT_SERIES.items()]

    def get_series_data(self, series_id: str, days: int = 365) -> List[Dict]:
        # Implementation using FredRepository
        with get_db_session() as db:
            repo = FredRepository(db)
            start_date = date.today() - timedelta(days=days)
            data = repo.get_series(series_id, start_date=start_date)
            return [d.to_dict() for d in data]

    def sync_series(self, series_id: str, series_type: str, days: int = 365):
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        data = self.fetch_series(series_id, start_date, end_date)
        if not data.empty:
            with get_db_session() as db:
                repo = FredRepository(db)
                repo.bulk_insert_from_dataframe(data, series_id, series_type)
