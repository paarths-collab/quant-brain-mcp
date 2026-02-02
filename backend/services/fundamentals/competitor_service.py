"""
competitor_service.py

Fetches and normalizes competitor (peer) data using
Financial Modeling Prep (FMP) API.
"""

from typing import List, Dict, Any
import requests
import logging


class CompetitorService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("FMP API key is required")
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/stable/stock-peers"

    def get_competitors(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch competitor companies for a given stock symbol.

        Args:
            symbol: Stock ticker (e.g., AAPL)

        Returns:
            List of competitors with standardized fields
        """
        try:
            url = f"{self.base_url}?symbol={symbol}&apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            raw_data = response.json()

            return self._normalize(raw_data)

        except Exception as e:
            logging.warning(f"Competitor fetch failed for {symbol}: {e}")
            return []

    # --------------------------------------------------
    # 🔧 Normalization
    # --------------------------------------------------

    @staticmethod
    def _normalize(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize FMP peer response.
        """
        competitors = []

        for item in raw:
            competitors.append({
                "symbol": item.get("symbol"),
                "company_name": item.get("companyName"),
                "price": item.get("price"),
                "market_cap": item.get("mktCap"),
            })

        return competitors
