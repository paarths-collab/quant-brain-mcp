"""
Shared data_loader pattern — self-contained, isolated copy for each module.
Uses yfinance under the hood. Each module gets its own copy so changes in one
do NOT affect any other.
"""
import pandas as pd
import yfinance as yf
from typing import Optional


def get_history(
    ticker: str,
    start: str,
    end: str,
    market: str = "us",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetch OHLCV history for a ticker using yfinance.
    Returns an empty DataFrame on failure.
    """
    try:
        ticker = ticker.strip().upper()
        market = (market or "us").strip().lower()

        # Auto-append .NS for Indian tickers if missing
        if market == "india":
            if not (ticker.endswith(".NS") or ticker.endswith(".BO")):
                ticker = f"{ticker}.NS"

        df = yf.download(
            ticker,
            start=start,
            end=end,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )

        if df.empty:
            return pd.DataFrame()

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)
        return df

    except Exception as e:
        print(f"[data_loader] get_history({ticker}) failed: {e}")
        return pd.DataFrame()


def format_ticker(ticker: str, market: str = "us") -> str:
    """Normalize ticker for a given market."""
    ticker = (ticker or "").strip().upper()
    if market.lower() == "india":
        if not (ticker.endswith(".NS") or ticker.endswith(".BO")):
            return f"{ticker}.NS"
    return ticker
