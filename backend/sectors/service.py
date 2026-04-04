import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Import from unified service layer
from backend.services.market_data import market_service

logger = logging.getLogger(__name__)

class SectorsService:
    """
    Module-specific service for Sector operations.
    Delegates all market data fetching to the unified MarketDataService.
    """
    
    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._indices_cache = {}
        self._constituents_cache = {}
        self._cache_ttl = 3600

    def _candidate_tickers(self, symbol: str, market: str) -> List[str]:
        """Build fallback ticker candidates for a symbol."""
        sym = (symbol or "").strip().upper()
        if not sym:
            return []

        candidates = [market_service.normalize_ticker(sym, market), sym]

        if market.lower() == "india":
            base = sym.replace(".NS", "").replace(".BO", "")
            candidates.extend([f"{base}.NS", f"{base}.BO", base])

        # Keep order stable, remove duplicates.
        deduped: List[str] = []
        seen = set()
        for c in candidates:
            if c and c not in seen:
                seen.add(c)
                deduped.append(c)
        return deduped

    def _resolve_quote(self, symbol: str, market: str, quotes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve a quote from existing batch result, then retry with ticker fallbacks."""
        for t in self._candidate_tickers(symbol, market):
            q = quotes.get(t, {})
            if q.get("price") is not None or q.get("change_percent") is not None:
                return q

        # Retry once with fallback tickers for stubborn symbols.
        candidates = self._candidate_tickers(symbol, market)
        retried = market_service.fetch_multiple_quotes(candidates)
        quotes.update(retried)

        for t in candidates:
            q = retried.get(t, {})
            if q.get("price") is not None or q.get("change_percent") is not None:
                return q

        return {}
        
        # Premium naming map for consistent display.
        self.INDEX_NAME_MAP = {
            "nifty_50": "Nifty 50",
            "nifty_next_50": "Nifty Next 50",
            "nifty_bank": "Bank Nifty",
            "nifty_it": "Nifty IT",
            "nifty_metal": "Nifty Metal",
            "nifty_realty": "Nifty Realty",
            "nifty_auto": "Nifty Auto",
            "nifty_energy": "Nifty Energy",
            "nifty_fmcg": "Nifty FMCG",
            "nifty_infra": "Nifty Infra",
            "nifty_pharma": "Nifty Pharma",
            "nifty_psu_bank": "Nifty PSU Bank",
            "nifty_private_bank": "Nifty Private Bank",
            "nifty_100": "Nifty 100",
            "nifty_200": "Nifty 200",
            "nifty_500": "Nifty 500",
            "nifty_midcap_100": "Nifty Midcap 100",
            "nifty_midcap_150": "Nifty Midcap 150",
            "nifty_midcap_50": "Nifty Midcap 50",
            "nifty_smallcap_100": "Nifty Smallcap 100",
            "nifty_smallcap_250": "Nifty Smallcap 250",
            "nifty_smallcap_50": "Nifty Smallcap 50",
            "nasdaq_100": "Nasdaq 100",
            "dow_jones": "Dow Jones",
            "sp_500_top": "S&P 500 (Top)",
            "us_tech_sector": "US Tech Sector",
            "us_financial_sector": "US Financial Sector",
            "us_healthcare_sector": "US Healthcare Sector",
            "us_energy_sector": "US Energy Sector",
            "us_consumer_discretionary": "US Consumer Discretionary",
            "us_smallcap_600": "US SmallCap 600",
        }

    def _get_market_indices(self, market: str) -> List[Dict[str, Any]]:
        market = market.lower()
        file_name = "us_indices.json" if market == "us" else "indian_indices.json"
        file_path = Path(__file__).resolve().parents[1] / "data" / file_name
        
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "indices" in data:
                        return data.get("indices", [])
                    return data if isinstance(data, list) else []
            except Exception as e:
                logger.error(f"Error loading {file_name}: {e}")
        return []

    def _load_csv_constituents(self, file_name: str) -> List[Dict[str, Any]]:
        if not file_name: return []
        file_path = Path(__file__).resolve().parents[1] / "data" / file_name
        if not file_path.exists(): return []
        
        results = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = row.get("Symbol", row.get("symbol"))
                    name = row.get("Company Name", row.get("name", ""))
                    if symbol:
                        results.append({"symbol": symbol, "name": name})
        except Exception as e:
            logger.error(f"Error loading CSV {file_name}: {e}")
        return results

    def get_indices_live(self, market: str = "india") -> List[Dict[str, Any]]:
        """[OPTIMIZED] Get all indices with real-time performance."""
        indices = self._get_market_indices(market)
        
        # Collect symbols and their likely fallbacks so India/US values populate more reliably.
        symbols_to_fetch = set()
        for idx in indices:
            sym = idx.get("symbol")
            if sym:
                for t in self._candidate_tickers(sym, market):
                    symbols_to_fetch.add(t)
            else:
                constituents = idx.get("constituents") or self._load_csv_constituents(idx.get("csv_file", ""))
                for c in constituents[:5]:
                    for t in self._candidate_tickers(c["symbol"], market):
                        symbols_to_fetch.add(t)

        # Bulk fetch using unified service
        # Validator is now standard in MarketDataService if we need it, 
        # but normalize_ticker handles most cases.
        quotes = market_service.fetch_multiple_quotes(list(symbols_to_fetch))
        
        results = []
        for idx in indices:
            sym = idx.get("symbol")
            if sym:
                q = self._resolve_quote(sym, market, quotes)
            else:
                # Derive from sample
                constituents = idx.get("constituents") or self._load_csv_constituents(idx.get("csv_file", ""))
                valid_changes = []
                for c in constituents[:5]:
                    q = self._resolve_quote(c["symbol"], market, quotes)
                    cp = q.get("change_percent")
                    if isinstance(cp, (int, float)):
                        valid_changes.append(cp)
                
                avg_change = sum(valid_changes) / len(valid_changes) if valid_changes else None
                q = {"price": None, "change_percent": avg_change}

            results.append({
                **idx,
                "change_percent": q.get("change_percent"),
                "price": q.get("price")
            })
        return results

    def get_index_constituents(self, index_id: str, market: str = "india", include_prices: bool = True) -> Dict[str, Any]:
        """Get listed stocks for a sector index with latest pricing."""
        indices = self._get_market_indices(market)
        idx_data = next((i for i in indices if i.get("id") == index_id), None)
        if not idx_data: return {"error": "Sector not found"}

        constituents = idx_data.get("constituents") or self._load_csv_constituents(idx_data.get("csv_file", ""))
        symbols = [
            market_service.normalize_ticker(c["symbol"], market)
            for c in constituents
            if isinstance(c, dict) and c.get("symbol")
        ]

        if not include_prices:
            return {
                "index": idx_data,
                "stocks": [
                    {**c, "price": None, "change_percent": None}
                    for c in constituents
                    if isinstance(c, dict) and c.get("symbol")
                ],
            }
        
        # Batch fetch primary symbols.
        quotes = market_service.fetch_multiple_quotes(symbols)
        
        stocks = []
        for c in constituents:
            if not isinstance(c, dict) or not c.get("symbol"):
                continue
            q = self._resolve_quote(c["symbol"], market, quotes)
            stocks.append({
                **c,
                "price": q.get("price"),
                "change_percent": q.get("change_percent")
            })
            
        return {"index": idx_data, "stocks": stocks}

# Global Instance
sectors_service = SectorsService()
