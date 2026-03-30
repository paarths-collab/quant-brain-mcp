import yfinance as yf
from typing import List, Dict

# Standard list of major US tech/finance stocks to build a representative treemap
# In production, this would be a database query of all 500 S&P stocks.
TOP_STOCKS = [
    # Technology
    "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM",
    # Communication
    "GOOGL", "META", "NFLX", "DIS",
    # Consumer Cyclical
    "AMZN", "TSLA", "HD", "MCD", "NKE",
    # Financial
    "JPM", "BAC", "V", "MA", "GS",
    # Healthcare
    "LLY", "JNJ", "UNH", "MRK",
    # Energy
    "XOM", "CVX",
]

def fetch_sector_performance() -> List[Dict]:
    """
    Fetches real-time performance for a basket of stocks to populate the Sector Treemap.
    Returns hierarchical structure: Sector -> Stock
    """
    try:
        # Fetch batch data
        tickers = yf.Tickers(" ".join(TOP_STOCKS))
        
        sector_map = {}
        
        for symbol in TOP_STOCKS:
            try:
                # Accessing .info for many stocks can be slow but yf.Tickers tries to optimize
                # However, for speed, we might want to prioritize just price change if possible.
                # But we need Sector info.
                 
                # Optimization: tickers.tickers[symbol].fast_info is faster for price/market_cap
                # but doesn't have sector. We might need to look up static sector map or use .info
                
                # Let's try .info but catch errors.
                # Note: yfinance batch info might still be serial in some versions.
                info = tickers.tickers[symbol].info
                
                sector = info.get("sector", "Unknown")
                mkt_cap = info.get("marketCap", 0)
                
                # percentChange is often not in .info, we might need to calc it
                # currentPrice - previousClose / previousClose
                current = info.get("currentPrice") or info.get("regularMarketPrice")
                prev = info.get("previousClose") or info.get("regularMarketOpen") # Approx fallback
                
                change_pct = 0
                if current and prev:
                    change_pct = ((current - prev) / prev) * 100
                
                if sector not in sector_map:
                    sector_map[sector] = []
                
                sector_map[sector].append({
                    "symbol": symbol,
                    "marketCap": mkt_cap,
                    "changePercent": round(change_pct, 2),
                    "sector": sector # Redundant but helpful for D3
                })
                
            except Exception as e:
                print(f"Skipping {symbol}: {e}")
                continue

        # Convert to list for D3 hierarchical input (or just flat list which D3 can group)
        # We will return a list of sectors, each containing stocks
        result = []
        for sect_name, stocks in sector_map.items():
            result.append({
                "name": sect_name,
                "children": stocks
            })
            
        return result
        
    except Exception as e:
        print(f"Error fetching sector data: {e}")
        return []
