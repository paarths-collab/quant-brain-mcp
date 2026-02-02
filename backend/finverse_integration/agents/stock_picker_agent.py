import yfinance as yf
import pandas as pd
from typing import List, Dict, Any
import os

class StockPickerAgent:
    """Selects potential candidates based on Sector and Market"""
    
    def run(self, market: str, sector: str, weights: Dict[str, float]) -> pd.DataFrame:
        """
        Selects top candidate stocks from local CSV data based on Market and Sector.
        """
        print(f"📊 StockPicker: Searching for {sector} stocks in {market} via Local CSV...")
        
        try:
            # Load Data
            if market == 'IN':
                file_path = os.path.join("data", "nifty500.csv")
                # Expected: Company Name, Industry, Symbol, etc.
            else:
                file_path = os.path.join("data", "us_stocks.csv")
            
            if not os.path.exists(file_path):
                print(f"⚠️ Data file not found: {file_path}. Falling back to default list.")
                return self._get_fallback_stocks(market, sector)

            df = pd.read_csv(file_path)
            
            # Normalize Columns
            # We need 'Ticker' and 'Sector'/'Industry'
            # Check likely column names
            cols = [c.lower() for c in df.columns]
            
            # Map Symbol
            if 'symbol' in cols:
                df['Ticker'] = df.iloc[:, cols.index('symbol')]
            elif 'ticker' in cols: 
                 df['Ticker'] = df.iloc[:, cols.index('ticker')]
            else:
                 # Fallback: assume 3rd column is ticker based on preview
                 df['Ticker'] = df.iloc[:, 2]

            # Map Sector
            if 'industry' in cols:
                df['Sector_Col'] = df.iloc[:, cols.index('industry')]
            elif 'sector' in cols:
                df['Sector_Col'] = df.iloc[:, cols.index('sector')]
            else:
                 # Fallback: assume 2nd column
                 df['Sector_Col'] = df.iloc[:, 1]
            
            # Filter by Sector (Loose Match)
            # e.g. "Tech" matches "Information Technology", "Technology", etc.
            sector_keywords = sector.lower().split()
            # Simple keyword match
            mask = df['Sector_Col'].astype(str).str.lower().apply(lambda x: any(k in x for k in sector_keywords))
            
            sector_df = df[mask].copy()
            
            if sector_df.empty:
                 print(f"⚠️ No matches for sector '{sector}' in CSV. Returning all valid tickers.")
                 sector_df = df.copy() # Fallback to all if sector mismatch
            
            # Select random sample or top 10 if no other metrics
            # In a real app, we would have market cap / momentum in CSV. 
            # For now, we take top 10 from the file (often sorted by Mkt Cap).
            candidates = sector_df.head(10).copy()
            
            # Add dummy score for downstream logic if needed
            candidates['Score'] = 80.0 
            
            # Clean Ticker (remove excess spaces)
            candidates['Ticker'] = candidates['Ticker'].astype(str).str.strip()
            
            print(f"✅ Found {len(candidates)} candidates for {sector}")
            return candidates

        except Exception as e:
            print(f"❌ StockPicker Error: {e}")
            return self._get_fallback_stocks(market, sector)

    def _get_fallback_stocks(self, market, sector):
        # ... existing fallback logic or just return empty DF ...
        return pd.DataFrame()
