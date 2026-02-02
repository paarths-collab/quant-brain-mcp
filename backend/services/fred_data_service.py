"""
FRED Data Service - Fetches and stores index prices from FRED API
"""
import os
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Any
from fredapi import Fred
import pandas as pd

from backend.database.connection import get_db_session
from backend.database.fred_repository import FredRepository


# Default FRED series for common indices
DEFAULT_INDEX_SERIES = {
    'SP500': {'type': 'index', 'title': 'S&P 500'},
    'DJIA': {'type': 'index', 'title': 'Dow Jones Industrial Average'},
    'NASDAQ100': {'type': 'index', 'title': 'NASDAQ 100'},
    'WILL5000IND': {'type': 'index', 'title': 'Wilshire 5000'},
    'VIXCLS': {'type': 'index', 'title': 'VIX Volatility Index'},
}

DEFAULT_RATE_SERIES = {
    'DGS10': {'type': 'rate', 'title': '10-Year Treasury Rate'},
    'DGS2': {'type': 'rate', 'title': '2-Year Treasury Rate'},
    'DGS30': {'type': 'rate', 'title': '30-Year Treasury Rate'},
    'FEDFUNDS': {'type': 'rate', 'title': 'Federal Funds Rate'},
    'DPRIME': {'type': 'rate', 'title': 'Bank Prime Loan Rate'},
}

DEFAULT_ECONOMIC_SERIES = {
    'CPIAUCSL': {'type': 'economic', 'title': 'Consumer Price Index'},
    'UNRATE': {'type': 'economic', 'title': 'Unemployment Rate'},
    'GDP': {'type': 'economic', 'title': 'Gross Domestic Product'},
    'INDPRO': {'type': 'economic', 'title': 'Industrial Production Index'},
}

# Commodity series (Oil, Gold, etc.)
DEFAULT_COMMODITY_SERIES = {
    'DCOILWTICO': {'type': 'commodity', 'title': 'Crude Oil WTI'},
    'DCOILBRENTEU': {'type': 'commodity', 'title': 'Crude Oil Brent'},
    'GASREGW': {'type': 'commodity', 'title': 'US Regular Gas Price'},
    'GOLDPMGBD228NLBM': {'type': 'commodity', 'title': 'Gold Price (London)'},
    'DEXUSEU': {'type': 'commodity', 'title': 'USD/EUR Exchange Rate'},
    'DEXJPUS': {'type': 'commodity', 'title': 'JPY/USD Exchange Rate'},
    'DEXUSUK': {'type': 'commodity', 'title': 'USD/GBP Exchange Rate'},
}

ALL_DEFAULT_SERIES = {**DEFAULT_INDEX_SERIES, **DEFAULT_RATE_SERIES, **DEFAULT_ECONOMIC_SERIES, **DEFAULT_COMMODITY_SERIES}


class FredDataService:
    """Service for fetching and managing FRED data"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        if not self.api_key:
            raise ValueError("FRED_API_KEY not found in environment")
        self.fred = Fred(api_key=self.api_key)
    
    def fetch_series(
        self,
        series_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.Series:
        """Fetch series data from FRED API"""
        try:
            data = self.fred.get_series(
                series_id,
                observation_start=start_date,
                observation_end=end_date
            )
            return data
        except Exception as e:
            print(f"Error fetching {series_id}: {e}")
            return pd.Series()
    
    def fetch_and_store_series(
        self,
        series_id: str,
        series_type: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Fetch from FRED and store in database"""
        # Set default date range (5 years)
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=365 * 5)
        
        # Fetch from FRED API
        data = self.fetch_series(series_id, start_date, end_date)
        
        if data.empty:
            return {
                "series_id": series_id,
                "status": "error",
                "message": "No data returned from FRED API",
                "count": 0
            }
        
        # Store in database
        with get_db_session() as db:
            repo = FredRepository(db)
            count = repo.bulk_insert_from_dataframe(data, series_id, series_type)
            
            # Update metadata
            series_info = ALL_DEFAULT_SERIES.get(series_id, {})
            repo.upsert_metadata( # type: ignore
                series_id=series_id,
                series_type=series_type,
                title=series_info.get('title', series_id)
            )
        
        return {
            "series_id": series_id,
            "series_type": series_type,
            "status": "success",
            "count": count,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
    
    def sync_all_indices(self, days: int = 365) -> List[Dict]:
        """Sync all default index series"""
        results = []
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        for series_id, info in DEFAULT_INDEX_SERIES.items():
            result = self.fetch_and_store_series(
                series_id, 
                info['type'],
                start_date,
                end_date
            )
            results.append(result)
        
        return results
    
    def sync_all_rates(self, days: int = 365) -> List[Dict]:
        """Sync all default rate series"""
        results = []
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        for series_id, info in DEFAULT_RATE_SERIES.items():
            result = self.fetch_and_store_series(
                series_id,
                info['type'],
                start_date,
                end_date
            )
            results.append(result)
        
        return results
    
    def sync_all(self, days: int = 365) -> Dict[str, List[Dict]]:
        """Sync all default series"""
        return {
            "indices": self.sync_all_indices(days),
            "rates": self.sync_all_rates(days)
        }
    
    def get_cached_series(
        self,
        series_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """Get series from database cache"""
        with get_db_session() as db:
            repo = FredRepository(db)
            data = repo.get_series(series_id, start_date, end_date) # type: ignore
            return [d.to_dict() for d in data]
    
    def get_cached_latest(self, series_ids: Optional[List[str]] = None) -> Dict[str, Dict]:
        """Get latest values for multiple series from cache"""
        if series_ids is None:
            series_ids = list(ALL_DEFAULT_SERIES.keys())
        
        with get_db_session() as db:
            repo = FredRepository(db)
            data = repo.get_multiple_series_latest(series_ids)
            return {k: v.to_dict() for k, v in data.items()}
    
    def get_series_with_fallback(
        self,
        series_id: str,
        series_type: str = 'index',
        max_age_hours: int = 24
    ) -> List[Dict]:
        """Get series from cache, fetch from API if stale"""
        with get_db_session() as db:
            repo = FredRepository(db)
            latest = repo.get_latest(series_id)
            
            # Check if data exists and is fresh
            if latest and latest.updated_at: # pyright: ignore[reportGeneralTypeIssues]
                age = datetime.utcnow() - latest.updated_at
                if age < timedelta(hours=max_age_hours): # type: ignore
                    # Return cached data
                    data = repo.get_series(series_id) # pyright: ignore[reportAttributeAccessIssue]
                    return [d.to_dict() for d in data]
        
        # Data is stale or missing, fetch fresh
        self.fetch_and_store_series(series_id, series_type)
        
        with get_db_session() as db:
            repo = FredRepository(db)
            data = repo.get_series(series_id) # pyright: ignore[reportAttributeAccessIssue]
            return [d.to_dict() for d in data]
    
    def get_index_dashboard(self) -> Dict[str, Any]:
        """Get dashboard data for all indices"""
        result = {
            "indices": [],
            "rates": [],
            "as_of": datetime.utcnow().isoformat()
        }
        
        with get_db_session() as db:
            repo = FredRepository(db)
            
            # Get indices
            for series_id, info in DEFAULT_INDEX_SERIES.items():
                latest = repo.get_latest(series_id)
                stats = repo.get_statistics(series_id, days=30)
                if latest:
                    result["indices"].append({
                        "series_id": series_id,
                        "title": info['title'],
                        "value": latest.value,
                        "date": latest.date.isoformat(),
                        "change_30d": stats.get('change_pct')
                    })
            
            # Get rates
            for series_id, info in DEFAULT_RATE_SERIES.items():
                latest = repo.get_latest(series_id)
                if latest:
                    result["rates"].append({
                        "series_id": series_id,
                        "title": info['title'],
                        "value": latest.value,
                        "date": latest.date.isoformat()
                    })
        
        return result
