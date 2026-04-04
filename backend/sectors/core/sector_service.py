from typing import List, Dict, Any
from backend.services.market_data import market_service

# Standard list of major US tech/finance stocks to build a representative treemap
# In production, this would be a database query of all 500 S&P stocks.
TOP_STOCKS = [
    # Technology
    "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM",
    # Communication
    "GOOGL", "META", "NFLX", "DIS",
    # Consumer Cyclical
    "AMZN", "TSLA", "HD", "MCD", "NKE",
    # Financial
    "JPM", "BAC", "V", "MA", "GS",
    # Healthcare
    "LLY", "JNJ", "UNH", "MRK",
    # Energy
    "XOM", "CVX",
]

def fetch_sector_performance() -> List[Dict[str, Any]]:
    """
    [OPTIMIZED] Fetches sector-grouped performance using centralized MarketDataService.
    Ensures 100% architectural consistency and resolves direct yfinance usage.
    """
    return market_service.fetch_sector_treemap_data(TOP_STOCKS)
