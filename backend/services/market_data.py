from typing import Dict, Any, List, Optional, Callable
import logging
import pandas as pd
from backend.core.safe_yfinance import (
    safe_fetch_history, 
    safe_fetch_info, 
    safe_get_price,
    safe_fetch_multiple_quotes,
    safe_fetch_candles
)

logger = logging.getLogger(__name__)

class MarketDataService:
    """
    Standard interface for all market data operations.
    Consolidates ticker normalization and provides a unified contract for all modules.
    """

    def normalize_ticker(self, ticker: str, market: str = "us") -> str:
        """
        Normalizes ticker based on market.
        - India: Appends .NS if missing
        - USA: returns as is
        """
        if not ticker:
            return ticker
            
        ticker = ticker.upper().strip()
        
        # Handle index mapping (e.g. NIFTY_50 -> ^NSEI)
        index_map = {
            "NIFTY_50": "^NSEI",
            "SENSEX": "^BSESN",
            "BANK_NIFTY": "^NSEBANK",
            "NIFTY_FIN_SERVICE": "NIFTY_FIN_SERVICE.NS" # Placeholder
        }
        
        if ticker in index_map:
            return index_map[ticker]

        if market.lower() == "india":
            if not (ticker.endswith(".NS") or ticker.endswith(".BO")):
                return f"{ticker}.NS"
                
        return ticker

    def get_current_price(self, ticker: str) -> float:
        """Get the most recent price for a ticker."""
        return safe_get_price(ticker) or 0.0

    def fetch_ohlcv(
        self, 
        ticker: str, 
        interval: str = "1d", 
        period: str = "1mo", 
        market: str = "us"
    ) -> pd.DataFrame:
        """
        Fetch OHLCV history as a clean, indexed DataFrame.
        Consolidates logic from localized data_loaders.
        """
        ticker = self.normalize_ticker(ticker, market)
        df = self.get_history(ticker, period=period, interval=interval)
        
        if df.empty:
            return pd.DataFrame()
            
        # Ensure consistent formatting
        df.index = pd.to_datetime(df.index)
        return df

    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1d",
        period: str = "1mo",
        start: Optional[str] = None,
        end: Optional[str] = None,
        market: str = "us",
    ) -> List[Dict[str, Any]]:
        """Compatibility wrapper returning candles as list of dicts."""
        if start or end:
            ticker = self.normalize_ticker(symbol, market)
            df = self.get_history(ticker, interval=interval, start=start, end=end)
            if df is None or df.empty:
                return []
            candles: List[Dict[str, Any]] = []
            for idx, row in df.iterrows():
                candles.append({
                    "date": idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                    "open": float(row.get('Open', 0)),
                    "high": float(row.get('High', 0)),
                    "low": float(row.get('Low', 0)),
                    "close": float(row.get('Close', 0)),
                    "volume": int(row.get('Volume', 0)),
                })
            return candles

        return safe_fetch_candles(symbol, interval=interval, period=period, market=market)

    def fetch_multiple_quotes(
        self, 
        symbols: List[str], 
        max_workers: int = 15, 
        validator: Optional[Callable] = None
    ) -> Dict[str, Dict]:
        """Fetch real-time quotes for multiple symbols."""
        return safe_fetch_multiple_quotes(symbols, max_workers, validator=validator)

    def get_history(
        self, 
        ticker: str, 
        period: str = "6mo", 
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> pd.DataFrame:
        """Get historical data as a pandas DataFrame."""
        res = safe_fetch_history(ticker, period=period, interval=interval, start=start, end=end)
        if res["status"] == "ok":
            return res["data"]
        return pd.DataFrame()

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive company/index metadata."""
        res = safe_fetch_info(ticker)
        return res.get("data", {})

    def fetch_sector_treemap_data(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        [CENTRALIZED] Gather sector and market cap data for a basket of stocks.
        Used for Treemaps (D3 hierarchical inputs).
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_single(symbol):
            try:
                info_res = safe_fetch_info(symbol)
                if info_res["status"] != "ok":
                    return None
                    
                info = info_res["data"]
                sector = info.get("sector", "Unknown")
                mkt_cap = info.get("marketCap", 0)
                
                # Fetch price change
                current = info.get("currentPrice") or info.get("regularMarketPrice")
                prev = info.get("previousClose")
                change_pct = 0
                if current and prev:
                    change_pct = ((current - prev) / prev) * 100
                
                return {
                    "symbol": symbol,
                    "marketCap": mkt_cap,
                    "changePercent": round(float(change_pct), 2),
                    "sector": sector
                }
            except Exception:
                return None

        sector_map = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_single, s): s for s in symbols}
            for future in as_completed(futures):
                res = future.result()
                if res:
                    sect = res["sector"]
                    if sect not in sector_map:
                        sector_map[sect] = []
                    sector_map[sect].append(res)

        # Convert to D3 structure
        return [{"name": name, "children": stocks} for name, stocks in sector_map.items()]

    def get_market_overview(self) -> Dict[str, Any]:
        """
        Get overview of major market indices, merging FRED and yfinance.
        Centralized from markets/data_service.py.
        """
        fred_map = {
            "SP500": "S&P 500",
            "DJIA": "Dow Jones",
            "NASDAQ100": "NASDAQ 100",
            "VIXCLS": "VIX",
        }

        yf_map = {
            "^NSEI": "NIFTY 50",
            "^BSESN": "SENSEX",
            "GC=F": "Gold"
        }

        overview: Dict[str, Any] = {}

        # 1. Try fetching from FRED (Macro)
        try:
            from backend.markets.fred_service import FredDataService
            service = FredDataService()
            for series_id, name in fred_map.items():
                try:
                    series = service.fetch_series(series_id)
                    if series is not None and not series.empty:
                        clean = series.dropna()
                        if not clean.empty:
                            current = float(clean.iloc[-1])
                            previous = float(clean.iloc[-2]) if len(clean) > 1 else current
                            change_pct = ((current - previous) / previous * 100) if previous else 0.0
                            
                            overview[series_id] = {
                                "name": name,
                                "price": current,
                                "change_pct": float(change_pct),
                                "source": "fred",
                                "date": clean.index[-1].date().isoformat() if hasattr(clean.index[-1], "date") else str(clean.index[-1])
                            }
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"FRED fetch failed in MarketDataService: {e}")

        # 2. Add yfinance indices in parallel
        from concurrent.futures import ThreadPoolExecutor
        
        def fetch_yf(symbol, name):
            res = safe_fetch_history(symbol, period="5d")
            if res["status"] != "ok":
                return None
            try:
                hist = res["data"]
                if hist is None or hist.empty: return None
                current = float(hist['Close'].iloc[-1])
                previous = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current
                change_pct = ((current - previous) / previous * 100) if previous else 0
                
                return symbol, {
                    "name": name,
                    "price": current,
                    "change_pct": float(change_pct),
                    "source": "yfinance",
                    "date": hist.index[-1].date().isoformat() if len(hist.index) else None,
                }
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=len(yf_map)) as executor:
            futures = [executor.submit(fetch_yf, s, n) for s, n in yf_map.items()]
            for future in futures:
                result = future.result()
                if result:
                    symbol, data = result
                    overview[symbol] = data

        return overview

# Singleton instance for platform-wide use
market_service = MarketDataService()
