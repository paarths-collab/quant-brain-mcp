"""
Graceful supply_chain_service stub for sectors/core.
Full supply chain data fetching is complex and not critical for server boot.
Returns empty/safe data to avoid import failures.
"""
from typing import List, Dict, Any


def fetch_supply_chain(ticker: str) -> Dict[str, Any]:
    """
    Returns an empty supply-chain graph structure.
    Replace with real implementation if supply chain feature is needed.
    """
    return {
        "ticker": ticker,
        "nodes": [],
        "edges": [],
        "suppliers": [],
        "customers": [],
        "status": "unavailable",
    }
