import os
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
FMP_BASE_URL = os.getenv("FMP_BASE_URL", "https://financialmodelingprep.com/api/v4")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
PEERS_PREMIUM = False

import requests
from typing import List, Dict


def fetch_stock_peers(symbol: str) -> List[Dict]:
    """
    Fetch peer companies for a given stock symbol from FMP.
    """
    url = f"https://financialmodelingprep.com/api/v4/stock_peers"
    params = {
        "symbol": symbol.upper(),
        "apikey": FMP_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        # Handle free-tier or plan limitations specifically
        if response.status_code == 403:
            print(f"Warning: Stock Peer Comparison requires an FMP Premium/Enterprise plan. Returning empty list.")
            return []
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching data from FMP: {e}")
        return [] # Return empty instead of crashing


    data = response.json()

    # Defensive check
    if not isinstance(data, list):
        return []

    peers = []
    for item in data:
        peers.append({
            "symbol": item.get("symbol"),
            "companyName": item.get("companyName"),
            "price": item.get("price"),
            "marketCap": item.get("mktCap"),
        })

    return peers

