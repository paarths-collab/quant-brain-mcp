import requests
from typing import List, Dict
from backend.core.config import FMP_API_KEY, FMP_BASE_URL


def fetch_stock_peers(symbol: str) -> List[Dict]:
    """
    Fetch peer companies for a given stock symbol from FMP.
    """
    url = f"{FMP_BASE_URL}/stock-peers"
    params = {
        "symbol": symbol.upper(),
        "apikey": FMP_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        # Log error or handle gracefully
        print(f"Error fetching data from FMP: {e}")
        raise RuntimeError(f"Failed to fetch peer data from FMP: {e}")

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
