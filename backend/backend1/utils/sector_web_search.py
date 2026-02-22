import re
import yfinance as yf
from ddgs import DDGS
import time
import random

class SectorWebSearch:

    def __init__(self, max_results=10):
        self.max_results = max_results
        self.blacklist = {
             "THE", "FOR", "IS", "TO", "OF", "AND", "OR", "IN", "ON", "AT", "BY", 
             "USA", "IPO", "AI", "CEO", "GDP", "USD", "INR", "ETF", "LTD", "INC", 
             "CORP", "PLC", "AG", "SA", "NV", "BSE", "NSE", "NYSE", "NASDAQ",
             "TOP", "BEST", "LIST", "VS", "NEW", "OLD", "BIG", "SMALL", "MID", "CAP"
        }

    def search_sector(self, sector_name, region=None):
        # 1. Determine Region / Query
        if region is None:
            region = "US"
            if any(x in sector_name.upper() for x in ["INDIA", "INDIAN", "NSE", "BSE", "NIFTY"]):
                region = "IN"
        else:
            # Map "India" to "IN" for internal consistency
            region = "IN" if region == "India" else region
             
        if region == "IN":
             query = f"Top NSE listed companies in {sector_name} ticker symbols list"
        else:
             query = f"Top publicly traded companies in {sector_name} ticker symbols list"

        print(f"Searching web for sector: {sector_name} (Region: {region})")

        raw_results = []
        try:
            with DDGS() as ddgs:
                # Use .text() for general search
                for r in ddgs.text(query, max_results=self.max_results):
                    raw_results.append(r.get("body", "") + " " + r.get("title", ""))
                    time.sleep(0.5) # Rate limit
        except Exception as e:
            print(f"DDG Search failed: {e}")
            return []

        tickers = self._extract_tickers(raw_results, region)
        print(f"Extracted candidates: {tickers}")
        
        validated = self._validate_tickers(tickers)
        print(f"Validated tickers: {validated}")

        return validated

    # -------------------------
    # Extract ticker symbols
    # -------------------------
    def _extract_tickers(self, texts, region="US"):
        found = set()
        
        # Regex: 2-6 chars, optional .NS suffix
        # If India, prefer .NS
        
        for text in texts:
            # Pattern 1: Explicit NSE/BSE tickers (e.g. RELIANCE.NS)
            if region == "IN":
                 matches = re.findall(r'\b[A-Z]{2,10}\.NS\b', text)
                 found.update(matches)
                 
                 # Pattern 2: Standalone caps (check later if they need suffix)
                 # matches_raw = re.findall(r'\b[A-Z]{3,10}\b', text)
                 # for m in matches_raw:
                 #    if m not in self.blacklist:
                 #        found.add(f"{m}.NS") 
            else:
                 # US Tickers (2-5 chars)
                 matches = re.findall(r'\b[A-Z]{1,5}\b', text)
                 found.update(matches)

        # Filter blacklist
        clean = {t for t in found if t.split('.')[0] not in self.blacklist}
        return list(clean)

    # -------------------------
    # Validate using yfinance
    # -------------------------
    def _validate_tickers(self, tickers):
        valid = []
        # Limit validation to avoid rate limits
        # Shuffle and take top 15 candidates to validate
        candidates = tickers[:15] 

        for t in candidates:
            try:
                stock = yf.Ticker(t)
                # Check 5d history - fast check for existence
                hist = stock.history(period="5d")

                if not hist.empty:
                    valid.append(t)
                    time.sleep(0.2) # Polite delay
                
                if len(valid) >= 8: # Stop once we have enough
                     break

            except Exception:
                continue

        return valid
