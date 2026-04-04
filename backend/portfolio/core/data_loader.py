from backend.services.market_data import market_service
import pandas as pd

def get_history(
    ticker: str,
    start: str,
    end: str,
    market: str = "us",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetch OHLCV history for a ticker using unified market_service.
    """
    try:
        return market_service.get_history(ticker, start=start, end=end, interval=interval)
    except Exception as e:
        print(f"[data_loader] get_history({ticker}) failed: {e}")
        return pd.DataFrame()


def format_ticker(ticker: str, market: str = "us") -> str:
    """Normalize ticker using unified market_service."""
    return market_service.normalize_ticker(ticker, market)
