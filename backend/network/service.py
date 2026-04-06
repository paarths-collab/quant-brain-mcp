import requests
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# --- Configuration (Local duplication for isolation) ---
FMP_API_KEY = os.getenv("FMP_API_KEY", "78b77a7605d81aa4f107f90f230cc00d")
logger = logging.getLogger(__name__)

def fetch_stock_peers(symbol: str) -> List[Dict]:
    """
    Fetch peer companies for a given stock symbol from FMP (Duplicated for isolation).
    """
    url = f"https://financialmodelingprep.com/api/v4/stock_peers"
    params = {"symbol": symbol.upper(), "apikey": FMP_API_KEY}
    if not FMP_API_KEY:
        logger.warning("FMP API key is missing; returning empty peers for %s", symbol)
        return []

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 403:
            logger.warning("FMP returned 403 for symbol=%s", symbol)
            return []
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            logger.warning("Unexpected FMP payload type for symbol=%s: %s", symbol, type(data).__name__)
            return []
        return [{"symbol": item.get("symbol"), "companyName": item.get("companyName"), "marketCap": item.get("mktCap")} for item in data]
    except requests.RequestException as exc:
        logger.warning("FMP request failed for symbol=%s: %s", symbol, exc)
        return []
    except ValueError as exc:
        logger.warning("FMP JSON decode failed for symbol=%s: %s", symbol, exc)
        return []
    except Exception as exc:
        logger.exception("Unexpected peer fetch error for symbol=%s: %s", symbol, exc)
        return []

class NetworkService:
    def get_network_graph(self, symbol: str) -> Dict[str, Any]:
        """
        Constructs a graph representation of the stock and its peers for D3.
        """
        symbol = symbol.upper()
        competitors = fetch_stock_peers(symbol)
        
        nodes = [{"id": symbol, "group": "root", "radius": 20}]
        links = []

        for peer in competitors[:10]:
            nodes.append({
                "id": peer['symbol'],
                "group": "competitor",
                "radius": 10,
                "marketCap": peer.get('marketCap')
            })
            links.append({"source": symbol, "target": peer['symbol'], "value": 1})
            
        return {"nodes": nodes, "links": links}

# --- Social / News Service Logic (Merged here) ---

class SocialService:
    def get_news_updates(self, query: str, limit: int = 12):
        """
        Placeholder for social news logic (to be filled from live_news_service / news_service).
        """
        return {"status": "success", "articles": []}
