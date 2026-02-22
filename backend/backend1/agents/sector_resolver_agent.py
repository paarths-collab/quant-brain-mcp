import json
import os
from backend.backend1.core.llm_client import LLMClient
from backend.backend1.utils.sector_web_search import SectorWebSearch

class SectorResolverAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.web_search = SectorWebSearch()
        self.us_indices_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "us_indices.json")
        self.ind_indices_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "indian_indices.json")
        
        self.sector_map = {}
        self._load_indices()

    def _load_indices(self):
        # Load US
        if os.path.exists(self.us_indices_path):
            with open(self.us_indices_path, "r") as f:
                data = json.load(f)
                for idx in data.get("indices", []):
                    # Map Name -> Tickers
                    tickers = [c["symbol"] for c in idx.get("constituents", [])]
                    self.sector_map[idx["name"].lower()] = tickers
                    self.sector_map[idx["id"].lower()] = tickers
                    # Heuristic mappings
                    if "semiconductor" in idx["name"].lower():
                         self.sector_map["semiconductors"] = tickers
                    if "technology" in idx["name"].lower():
                         self.sector_map["tech"] = tickers

        # Load India
        if os.path.exists(self.ind_indices_path):
            with open(self.ind_indices_path, "r") as f:
                data = json.load(f)
                for idx in data.get("indices", []):
                    tickers = [c["symbol"] for c in idx.get("constituents", [])]
                    self.sector_map[idx["name"].lower()] = tickers
                    self.sector_map[idx["id"].lower()] = tickers

    def resolve_sector(self, sector_name: str):
        sector_key = sector_name.lower().strip()
        
        # Check direct match or partial match
        if sector_key in self.sector_map:
            return self.sector_map[sector_key]
        
        for k, v in self.sector_map.items():
            if sector_key in k:
                return v

        # Fallback to Deterministic Web Search + Regex Validation
        print(f"Sector '{sector_name}' not found locally. Using Robust Web Search.")
        tickers = self.web_search.search_sector(sector_name)
        
        if tickers:
            # Cache it in memory for session
            self.sector_map[sector_key] = tickers
            return tickers
            
        print(f"Could not resolve tickers for sector: {sector_name}")
        return []
