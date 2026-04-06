import csv
import json
import logging
import time
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
        self._market_indices_cache = {}
        self._live_indices_cache = {}
        self._cache_ttl = 3600
        self._live_cache_ttl = 60

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
        q = self._lookup_quote_from_prefetched(symbol, market, quotes)
        if q:
            return q

        # Retry once with fallback tickers for stubborn symbols.
        candidates = self._candidate_tickers(symbol, market)
        retried = market_service.fetch_multiple_quotes(candidates)
        quotes.update(retried)

        for t in candidates:
            q = retried.get(t, {})
            if q.get("price") is not None or self._extract_change_percent(q) is not None:
                return q

        return {}

    def _lookup_quote_from_prefetched(
        self,
        symbol: str,
        market: str,
        quotes: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Resolve quote from existing prefetched batch only (no network retries)."""
        for t in self._candidate_tickers(symbol, market):
            q = quotes.get(t, {})
            if q.get("price") is not None or self._extract_change_percent(q) is not None:
                return q
        return {}

    def _extract_change_percent(self, quote: Dict[str, Any]) -> Any:
        """Read normalized change percent from multiple possible key names."""
        if not isinstance(quote, dict):
            return None
        cp = quote.get("change_percent")
        if cp is None:
            cp = quote.get("change_pct")
        return cp

    def _constituent_avg_change(
        self,
        constituents: List[Dict[str, Any]],
        market: str,
        quotes: Dict[str, Dict[str, Any]],
        sample_size: int = 12,
    ) -> Any:
        """Compute average change from a sample of constituent quotes."""
        valid_changes = []
        for c in constituents[:sample_size]:
            sym = c.get("symbol")
            if not sym:
                continue
            q = self._lookup_quote_from_prefetched(sym, market, quotes)
            cp = self._extract_change_percent(q)
            if isinstance(cp, (int, float)):
                valid_changes.append(cp)

        if not valid_changes:
            return None
        return sum(valid_changes) / len(valid_changes)
        
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
        cached = self._market_indices_cache.get(market)
        if cached and (time.time() - cached.get("cached_at", 0) < self._cache_ttl):
            return cached.get("data", [])

        file_name = "us_indices.json" if market == "us" else "indian_indices.json"
        file_path = Path(__file__).resolve().parents[1] / "data" / file_name
        
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "indices" in data:
                        result = data.get("indices", [])
                    else:
                        result = data if isinstance(data, list) else []
                    self._market_indices_cache[market] = {"data": result, "cached_at": time.time()}
                    return result
            except Exception as e:
                logger.error(f"Error loading {file_name}: {e}")
        return []

    def _load_csv_constituents(self, file_name: str) -> List[Dict[str, Any]]:
        if not file_name: return []
        cached = self._constituents_cache.get(file_name)
        if cached and (time.time() - cached.get("cached_at", 0) < self._cache_ttl):
            return cached.get("data", [])

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
            self._constituents_cache[file_name] = {"data": results, "cached_at": time.time()}
        except Exception as e:
            logger.error(f"Error loading CSV {file_name}: {e}")
        return results

    def get_indices_live(self, market: str = "india") -> List[Dict[str, Any]]:
        """[OPTIMIZED] Get all indices with real-time performance."""
        market_key = (market or "india").lower()
        cached = self._live_indices_cache.get(market_key)
        if cached and (time.time() - cached.get("cached_at", 0) < self._live_cache_ttl):
            return cached.get("data", [])

        previous_snapshot = cached.get("data", []) if cached else []
        previous_by_id = {
            item.get("id"): item
            for item in previous_snapshot
            if isinstance(item, dict) and item.get("id")
        }

        indices = self._get_market_indices(market)

        # Fetch index symbols first, then a small constituent sample per index.
        symbols_to_fetch = set()
        for idx in indices:
            sym = idx.get("symbol")
            if sym:
                for t in self._candidate_tickers(sym, market):
                    symbols_to_fetch.add(t)

            constituents = idx.get("constituents") or self._load_csv_constituents(idx.get("csv_file", ""))
            for constituent in constituents[:2]:
                constituent_symbol = constituent.get("symbol")
                if constituent_symbol:
                    symbols_to_fetch.add(market_service.normalize_ticker(constituent_symbol, market))

        # Bulk fetch using unified service
        quotes = market_service.fetch_multiple_quotes(list(symbols_to_fetch))

        results = []
        for idx in indices:
            sym = idx.get("symbol")
            q = {}
            cp = None
            price = None
            if sym:
                q = self._lookup_quote_from_prefetched(sym, market, quotes)
                cp = self._extract_change_percent(q)
                price = q.get("price")

                if cp is None:
                    constituents = idx.get("constituents") or self._load_csv_constituents(idx.get("csv_file", ""))
                    cp = self._constituent_avg_change(constituents, market, quotes, sample_size=6)

                if price is None:
                    constituents = idx.get("constituents") or self._load_csv_constituents(idx.get("csv_file", ""))
                    sample_prices = []
                    for c in constituents[:6]:
                        csym = c.get("symbol") if isinstance(c, dict) else None
                        if not csym:
                            continue
                        cq = self._lookup_quote_from_prefetched(csym, market, quotes)
                        cprice = cq.get("price")
                        if isinstance(cprice, (int, float)):
                            sample_prices.append(cprice)
                    if sample_prices:
                        price = round(sum(sample_prices) / len(sample_prices), 2)
            else:
                # Derive from sample
                constituents = idx.get("constituents") or self._load_csv_constituents(idx.get("csv_file", ""))
                cp = self._constituent_avg_change(constituents, market, quotes, sample_size=6)

            prev = previous_by_id.get(idx.get("id"), {})
            if price is None and prev.get("price") is not None:
                price = prev.get("price")
            if cp is None and prev.get("change_percent") is not None:
                cp = prev.get("change_percent")

            results.append({
                **idx,
                "change_percent": cp,
                "price": price
            })

        self._live_indices_cache[market_key] = {"data": results, "cached_at": time.time()}
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

        # Build a single fallback retry batch for symbols that still have no quote.
        missing_symbols = []
        for c in constituents:
            if not isinstance(c, dict) or not c.get("symbol"):
                continue
            q = self._lookup_quote_from_prefetched(c["symbol"], market, quotes)
            if q.get("price") is None and self._extract_change_percent(q) is None:
                missing_symbols.append(c["symbol"])

        if missing_symbols:
            fallback_candidates = []
            for symbol in missing_symbols[:20]:
                fallback_candidates.extend(self._candidate_tickers(symbol, market))

            retry_quotes = market_service.fetch_multiple_quotes(list(set(fallback_candidates)), max_workers=10)
            quotes.update(retry_quotes)
        
        stocks = []
        for c in constituents:
            if not isinstance(c, dict) or not c.get("symbol"):
                continue
            q = self._lookup_quote_from_prefetched(c["symbol"], market, quotes)
            stocks.append({
                **c,
                "price": q.get("price"),
                "change_percent": self._extract_change_percent(q)
            })
            
        return {"index": idx_data, "stocks": stocks}

# Global Instance
sectors_service = SectorsService()
