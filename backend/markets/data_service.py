from typing import Dict, Any, List, Optional
from backend.services.market_data import market_service
from backend.services.technical_analysis import technical_service

# Note: Markets domain still owns Macro/FRED specific logic 
# but delegates all standard OHLCV/Quotes to the unified service layer.

def fetch_candles(
    symbol: str,
    interval: str = "1d",
    period: str = "1mo",
    market: str = "us"
) -> List[Dict[str, Any]]:
    """[DELEGATED] Fetch candles using unified market service."""
    # MarketDataService handles normalization and safety
    return market_service.fetch_candles(symbol, interval=interval, period=period, market=market)

def fetch_multiple_quotes(symbols: List[str], max_workers: int = 15, validator: Optional[Any] = None) -> Dict[str, Dict]:
    """[DELEGATED] Fetch multiple quotes using unified market service."""
    return market_service.fetch_multiple_quotes(symbols, max_workers, validator=validator)

def get_market_overview() -> Dict[str, Any]:
    """[DELEGATED] Get centralized market overview (FRED + YFinance)."""
    return market_service.get_market_overview()

def get_current_price(ticker: str) -> float:
    """[DELEGATED] Get price using unified market service."""
    return market_service.get_current_price(ticker)

def calculate_indicators(ticker: str, range: str = "6mo", interval: str = "1d", market: str = "us") -> Dict[str, Any]:
    """[DELEGATED] Get indicators using unified technical service."""
    return technical_service.calculate_indicators(ticker, range_period=range, interval=interval, market=market)

class MarketDataService:
    """
    [DELEGATED] Thin compatibility layer for the Markets domain.
    Delegates all operations to the global backend.services.market_data.
    """
    def normalize_ticker(self, ticker: str, market: str = "us") -> str:
        return market_service.normalize_ticker(ticker, market)

    def get_history(self, ticker: str):
        return market_service.get_history(ticker)

    def get_fundamentals(self, ticker: str):
        return market_service.get_fundamentals(ticker)
