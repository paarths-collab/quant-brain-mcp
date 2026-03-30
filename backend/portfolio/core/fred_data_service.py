"""
Isolated FredDataService — self-contained copy for this module.
Uses fredapi library. Each module gets its own copy.
"""
import os
from typing import Optional
import pandas as pd


class FredDataService:
    """Fetches macroeconomic data from the FRED API."""

    def __init__(self):
        self._api_key = os.getenv("FRED_API_KEY", "")
        self._fred = None

    def _get_fred(self):
        if self._fred is None:
            try:
                from fredapi import Fred
                self._fred = Fred(api_key=self._api_key)
            except ImportError:
                print("[FredDataService] fredapi not installed. FRED data unavailable.")
                self._fred = False
        return self._fred

    def fetch_series(self, series_id: str, limit: int = 30) -> Optional[pd.Series]:
        """Fetch a FRED data series by ID. Returns None on failure."""
        try:
            fred = self._get_fred()
            if not fred:
                return None
            data = fred.get_series(series_id)
            if data is not None and not data.empty:
                return data.tail(limit)
            return None
        except Exception as e:
            print(f"[FredDataService] fetch_series({series_id}) failed: {e}")
            return None

    def get_series_info(self, series_id: str) -> dict:
        """Fetch metadata about a FRED series."""
        try:
            fred = self._get_fred()
            if not fred:
                return {}
            info = fred.get_series_info(series_id)
            return info.to_dict() if info is not None else {}
        except Exception as e:
            print(f"[FredDataService] get_series_info({series_id}) failed: {e}")
            return {}
