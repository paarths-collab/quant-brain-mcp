"""
peer_valuation_service.py

Fetches valuation metrics for peer comparison.
"""

import requests
from typing import List, Dict, Any


class PeerValuationService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/stable/key-metrics-ttm"

    def get_peer_valuations(self, symbols: List[str]) -> List[Dict[str, Any]]:
        results = []

        for symbol in symbols:
            try:
                url = f"{self.base_url}/{symbol}?apikey={self.api_key}"
                r = requests.get(url, timeout=10)
                data = r.json()

                if not data:
                    continue

                d = data[0]
                results.append({
                    "symbol": symbol,
                    "pe_ratio": d.get("peRatioTTM"),
                    "ev_ebitda": d.get("enterpriseValueOverEBITDATTM"),
                })
            except Exception:
                continue

        return results


        def rank_by_market_cap(peers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        peers,
        key=lambda x: x.get("market_cap", 0),
        reverse=True
    )
