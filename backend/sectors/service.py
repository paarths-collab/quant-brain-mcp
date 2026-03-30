import csv
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import pandas as pd
import yfinance as yf

# Import from existing or core as needed
from .core.market_data_service import fetch_multiple_quotes

logger = logging.getLogger(__name__)

class SectorsService:
    """
    Consolidated service for all Sector-related operations (Treemap, Intel, Resolution).
    Replaces treemap_service.py, sector_service.py, sector_resolver.py, etc.
    """
    
    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._indices_cache = {}
        self._cache_ttl = 3600 # 1 hour

    def _cache_key(self, prefix: str, market: str) -> str:
        return f"sectors:{prefix}:{market}"

    def _cache_get_json(self, key: str) -> Any:
        try:
            if self._redis:
                val = self._redis.get(key)
                return json.loads(val) if val else None
            return self._indices_cache.get(key)
        except Exception:
            return None

    def _cache_set_json(self, key: str, value: Any, ttl: int = None):
        try:
            if self._redis:
                self._redis.setex(key, ttl or self._cache_ttl, json.dumps(value))
            else:
                self._indices_cache[key] = value
        except Exception:
            pass

    # --- Core Index/Metadata Logic ---

    def _get_market_indices(self, market: str = "india") -> List[Dict[str, Any]]:
        """Get list of base indices (Benchmark + Broad Market CSVs)"""
        key = self._cache_key("indices_meta", market)
        cached = self._cache_get_json(key)
        if isinstance(cached, list):
            return cached
            
        # 1. Load benchmark indices from JSON
        indices = self._load_benchmark_indices(market)
        
        # 2. Load broad market indices from CSV catalog
        csv_indices = self._build_csv_index_catalog(market)
        
        combined = indices + csv_indices
        self._cache_set_json(key, combined)
        return combined

    def _load_benchmark_indices(self, market: str) -> List[Dict[str, Any]]:
        data_dir = Path(__file__).parent.parent / "data"
        file_name = "indian_indices.json" if market.lower() == "india" else "us_indices.json"
        try:
            with open(data_dir / file_name, "r") as f:
                data = json.load(f)
                return data.get("indices", [])
        except Exception:
            return []

    def _build_csv_index_catalog(self, market: str) -> List[Dict[str, Any]]:
        data_dir = Path(__file__).parent.parent / "data"
        csv_files = sorted(data_dir.glob("*.csv"))
        catalog = []
        seen_ids = set()

        for csv_file in csv_files:
            if not self._is_market_csv(csv_file.stem, market):
                continue
            
            index_id = csv_file.stem.lower()
            if index_id in seen_ids: continue
            
            # Simple count
            try:
                with open(csv_file, "r", encoding="utf-8-sig", errors="ignore") as f:
                    count = sum(1 for _ in f) - 1
                    if count < 0: count = 0
            except:
                count = 0

            catalog.append({
                "id": index_id,
                "name": index_id.replace("_", " ").upper(),
                "symbol": None,
                "exchange": "NSE" if market == "india" else "NYSE",
                "type": "Broad Market",
                "description": f"Constituents from {csv_file.name}",
                "csv_file": csv_file.name,
                "constituents_count": count,
                "constituents": [] # Lazy
            })
            seen_ids.add(index_id)
        return catalog

    def _is_market_csv(self, stem: str, market: str) -> bool:
        if market.lower() == "india":
            return stem.startswith("ind_") or "nifty" in stem.lower()
        return stem.startswith("us_") or stem.endswith("_indices")

    def _load_csv_constituents(self, csv_file_name: str) -> List[Dict[str, Any]]:
        data_dir = Path(__file__).parent.parent / "data"
        path = data_dir / csv_file_name
        if not path.exists(): return []
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            # Simple symbol/name detection
            constituents = []
            for row in rows:
                symbol = (row.get("symbol") or row.get("ticker") or row.get("Symbol") or "").strip()
                name = (row.get("name") or row.get("company name") or row.get("Name") or "").strip()
                if symbol: constituents.append({"symbol": symbol, "name": name})
            return constituents
        except:
            return []

    # --- Optimized Public API ---

    def get_indices_live(self, market: str = "india") -> List[Dict[str, Any]]:
        """
        [OPTIMIZED] Get all indices with prices.
        Uses BULK FETCHING for constituent-derived indices.
        """
        indices = self._get_market_indices(market)
        
        # 1. Collect all symbols needed for prices
        all_symbols_to_fetch = set()
        for idx in indices:
            if idx.get("symbol"):
                all_symbols_to_fetch.add(idx["symbol"])
            elif idx.get("csv_file"):
                # Sample the first 5 for speed
                constituents = self._load_csv_constituents(idx["csv_file"])
                idx["_sample"] = constituents[:5]
                for c in idx["_sample"]:
                    if c.get("symbol"): all_symbols_to_fetch.add(c["symbol"])

        # 2. BULK FETCH all quotes in ONE call
        symbols_list = list(all_symbols_to_fetch)
        # Ensure .NS for Indian stocks if missing
        if market.lower() == "india":
            symbols_list = [s if (s.startswith("^") or s.endswith(".NS") or s.endswith(".BO")) else f"{s}.NS" for s in symbols_list]
        
        logger.info(f"[SectorsService] Bulk fetching {len(symbols_list)} quotes...")
        quotes = fetch_multiple_quotes(symbols_list)
        
        # 3. Build results and map back derived changes
        results = []
        for idx in indices:
            symbol = idx.get("symbol")
            if symbol:
                quote_key = symbol if (not market == "india" or symbol.startswith("^")) else f"{symbol}.NS"
                quote = quotes.get(quote_key, {})
                change_pct = quote.get("change_percent")
            else:
                # Derive from sample
                sample = idx.get("_sample", [])
                valid_changes = []
                for c in sample:
                    s = c["symbol"]
                    q_key = s if (not market == "india" or s.startswith("^")) else f"{s}.NS"
                    q = quotes.get(q_key, {})
                    if q.get("change_percent") is not None:
                        valid_changes.append(q["change_percent"])
                
                change_pct = sum(valid_changes) / len(valid_changes) if valid_changes else None
                quote = {"price": None, "change_percent": change_pct}

            results.append({
                **idx,
                "change_percent": change_pct,
                "price": quote.get("price"),
                "currency": "₹" if market == "india" else "$"
            })
        return results

    def get_index_constituents(self, index_id: str, market: str = "india", live: bool = True) -> Dict[str, Any]:
        """Get detailed stock list for an index"""
        indices = self._get_market_indices(market)
        idx_data = next((i for i in indices if i["id"] == index_id), None)
        if not idx_data: return {"error": "Not found"}

        constituents = idx_data.get("constituents", [])
        if not constituents and idx_data.get("csv_file"):
            constituents = self._load_csv_constituents(idx_data["csv_file"])
        
        if not live:
            return {"index": idx_data, "stocks": constituents}

        # Fetch prices
        symbols = [c["symbol"] for c in constituents if c.get("symbol")]
        if market.lower() == "india":
            symbols = [s if (s.startswith("^") or s.endswith(".NS")) else f"{s}.NS" for s in symbols]
        
        logger.info(f"[SectorsService] Fetching {len(symbols)} stocks for index {index_id}")
        quotes = fetch_multiple_quotes(symbols)
        
        stocks = []
        for c in constituents:
            sym = c["symbol"]
            q_key = sym if (not market == "india" or sym.startswith("^")) else f"{sym}.NS"
            q = quotes.get(q_key, {})
            stocks.append({**c, "change_percent": q.get("change_percent"), "price": q.get("price")})
            
        return {"index": idx_data, "stocks": stocks}

# Global Instance
sectors_service = SectorsService()
