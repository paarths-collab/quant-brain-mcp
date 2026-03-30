"""
Isolated peers_service for network/core.
Fetches stock peers/competitors using yfinance and FMP data.
Modifying this does NOT affect peers/ module.
"""
import os
import yfinance as yf
from typing import List, Dict, Any


def fetch_stock_peers(ticker: str, limit: int = 10) -> List[str]:
    """
    Fetch peer/competitor tickers for a given stock.
    Uses yfinance info first, falls back to sector-based lookup.
    """
    try:
        ticker = ticker.upper().strip()
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        # Check if yfinance has recommendationKey or similar
        # Try FMP API for peers if available
        fmp_key = os.getenv("FMP_API_KEY", "")
        if fmp_key:
            import urllib.request
            import json
            url = f"https://financialmodelingprep.com/api/v4/stock_peers?symbol={ticker}&apikey={fmp_key}"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
                if data and isinstance(data, list) and "peersList" in data[0]:
                    peers = data[0]["peersList"][:limit]
                    return [p for p in peers if p != ticker]

        # Fallback: same sector ETF method — return empty if no API key
        return []

    except Exception as e:
        print(f"[peers_service] fetch_stock_peers({ticker}) failed: {e}")
        return []


def get_peers_with_metrics(ticker: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Fetch peers with basic price and valuation metrics."""
    peers = fetch_stock_peers(ticker, limit=limit)
    if not peers:
        return []

    results = []
    for peer in peers:
        try:
            t = yf.Ticker(peer)
            info = t.info or {}
            results.append({
                "ticker": peer,
                "name": info.get("shortName") or info.get("longName") or peer,
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("forwardPE") or info.get("trailingPE"),
                "sector": info.get("sector", "N/A"),
            })
        except Exception:
            results.append({"ticker": peer, "name": peer})

    return results
