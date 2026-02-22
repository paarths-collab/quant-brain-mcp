import json
import os
import yfinance as yf
# Assuming existing SectorWebSearch is accessible here, or I need to fix imports if I moved it
# Actually check where SectorWebSearch is: backend/backend1/utils/sector_web_search.py
from backend.backend1.utils.sector_web_search import SectorWebSearch

class SectorResolver:
    def __init__(self):
        # Resolve paths relative to this file
        # This file is in backend/services/
        # base_dir = backend/
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data")
        
        self.us_indices_path = os.path.join(self.data_dir, "us_indices.json")
        self.ind_indices_path = os.path.join(self.data_dir, "indian_indices.json")
        self.metadata_path = os.path.join(self.data_dir, "ticker_metadata.json")
        
        self.sector_map = {}
        self.metadata_cache = {}
        
        self.web_search = SectorWebSearch()
        
        self._load_data()

    def _load_data(self):
        """Loads indices and metadata cache."""
        # 1. Load Indices (Hardcoded Sector Map)
        self._load_indices_file(self.us_indices_path)
        self._load_indices_file(self.ind_indices_path)

        # 2. Load Ticker Metadata Cache
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r") as f:
                    self.metadata_cache = json.load(f)
            except Exception as e:
                print(f"Error loading metadata cache: {e}")

    def _load_indices_file(self, path):
        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    data = json.load(f)
                    for idx in data.get("indices", []):
                        tickers = [c["symbol"] for c in idx.get("constituents", [])]
                        # Map ID and Name
                        self.sector_map[idx["id"].lower()] = tickers
                        self.sector_map[idx["name"].lower()] = tickers
                        
                        # Apply to specific keywords
                        name = idx["name"].lower()
                        if "semiconductor" in name:
                            self.sector_map["semiconductors"] = tickers
                        if "technology" in name:
                            self.sector_map["tech"] = tickers
                            
                except Exception as e:
                    print(f"Error loading indices from {path}: {e}")

    def resolve_sector(self, sector_name: str, region: str = "US"):
        """
        Resolves a sector name (or theme) to a list of tickers.
        Priority:
        1. Theme -> Sector Mapping
        2. Direct Index Match
        3. Metadata Search
        4. Web Search Fallback
        
        Filters results by Region (US vs India).
        """
        raw_key = sector_name.lower().strip()
        print(f"Resolving Sector/Theme: '{sector_name}' ({region})")

        # --- Strategy 0: Theme Mapping ---
        # Map "AI" -> "Technology" before searching
        mapped_sector = self._map_theme_to_sector(raw_key, region)
        search_key = mapped_sector.lower() if mapped_sector else raw_key
        
        if mapped_sector:
             print(f"Mapped Theme '{sector_name}' -> Sector '{mapped_sector}'")

        tickers = []
        
        # --- Strategy 1: Direct Index Map Match ---
        found = False
        if search_key in self.sector_map:
            print(f"Found direct index match for '{search_key}'")
            tickers = self.sector_map[search_key]
            found = True
        
        if not found:
            # Partial key match
            for k, v in self.sector_map.items():
                if search_key in k:
                    print(f"Found partial index match: '{k}'")
                    tickers = v
                    found = True
                    break

        # --- Strategy 2: Metadata Filtering ---
        if not found:
            print("Searching metadata cache...")
            meta_tickers = self._search_metadata(search_key)
            if len(meta_tickers) >= 5:
                 print(f"Found {len(meta_tickers)} matches in metadata.")
                 tickers = list(meta_tickers)
                 found = True
            else:
                 # If we have some meta matches, keep them but try web search too
                 tickers = list(meta_tickers)

        # --- Strategy 3: Web Search Fallback ---
        if not found or len(tickers) < 5:
            print(f"Metadata insufficient. Falling back to Web Search for '{search_key}'...")
            web_tickers = self.web_search.search_sector(search_key, region=region)
            if web_tickers:
                print(f"Web search found {len(web_tickers)} tickers.")
                tickers = list(set(tickers + web_tickers))

        # --- FINAL: Region Filtering ---
        filtered_tickers = self._filter_by_region(tickers, region)
        print(f"DEBUG: resolve_sector result: {filtered_tickers}")
        print(f"Final Resolved Universe: {len(filtered_tickers)} tickers ({region})")
        
        return filtered_tickers

    def _map_theme_to_sector(self, theme_key: str, region: str):
        us_map = {
            "ai": "Technology",
            "artificial intelligence": "Technology",
            "semiconductor": "Technology",
            "chip": "Technology",
            "cybersecurity": "Technology",
            "cloud": "Technology",
            "ev": "Automotive",
            "electric vehicle": "Automotive",
            "fintech": "Financial Services",
            "pharma": "Healthcare",
            "defense": "Aerospace & Defense"
        }
        
        india_map = {
            "ai": "IT", 
            "artificial intelligence": "IT",
            "semiconductor": "IT", 
            "chip": "IT",
            "cybersecurity": "IT",
            "cloud": "IT",
            "ev": "Automobile",
            "electric vehicle": "Automobile",
            "fintech": "Bank",
            "pharma": "Pharma",
            "defense": "Defence", 
            "bank": "Bank",
            "banking": "Bank"
        }
        
        target_map = india_map if region == "India" else us_map
        
        # Check exact or partial
        for k, v in target_map.items():
            if k in theme_key:
                return v
        return None

    def _search_metadata(self, key):
        matched = set()
        search_terms = key.split()
        for ticker, meta in self.metadata_cache.items():
            m_sector = meta.get("sector", "").lower() if meta.get("sector") else ""
            m_industry = meta.get("industry", "").lower() if meta.get("industry") else ""
            combined = f"{m_sector} {m_industry}"
            
            if key in m_sector or key in m_industry:
                matched.add(ticker)
            elif all(term in combined for term in search_terms):
                matched.add(ticker)
        return matched

    def _filter_by_region(self, tickers, region):
        filtered = []
        for t in tickers:
            is_india = t.endswith(".NS") or t.endswith(".BO")
            if region == "India" and is_india:
                filtered.append(t)
            elif region == "US" and not is_india:
                filtered.append(t)
        return filtered
