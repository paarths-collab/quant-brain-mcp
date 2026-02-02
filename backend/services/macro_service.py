import yfinance as yf
from typing import Dict, List, Any

# Map of macro indicators to Yahoo Finance Tickers
MACRO_TICKERS = {
    "crude_oil": "CL=F",
    "gold": "GC=F",
    "silver": "SI=F",
    "us_10y": "^TNX",
    "india_10y": "^IGXB", # Or suitable ticker, often hard to find exact live one on YF free. Using US and Global mostly.
    "bitcoin": "BTC-USD",
    "eur_usd": "EURUSD=X"
}

# Static dataset for Globe Visualization (Demo Data)
# In a real app, this would come from a specialized commodities database.
COMMODITY_LOCATIONS = {
    "oil": [
        {"name": "Ghawar Field", "country": "Saudi Arabia", "lat": 24.5, "lng": 49.5, "type": "Extraction", "capacity": "3.8M bpd"},
        {"name": "Permian Basin", "country": "USA", "lat": 31.5, "lng": -102.5, "type": "Extraction", "capacity": "4.5M bpd"},
        {"name": "Jamnagar Refinery", "country": "India", "lat": 22.4, "lng": 70.0, "type": "Refinery", "capacity": "1.24M bpd"},
        {"name": "Cushing Storage", "country": "USA", "lat": 35.9, "lng": -96.7, "type": "Storage", "capacity": "Hub"},
    ],
    "gold": [
        {"name": "Witwatersrand Basin", "country": "South Africa", "lat": -26.2, "lng": 27.9, "type": "Mine"},
        {"name": "Carlin Trend", "country": "USA", "lat": 40.9, "lng": -116.3, "type": "Mine"},
        {"name": "Boddington", "country": "Australia", "lat": -32.7, "lng": 116.3, "type": "Mine"},
    ]
}

def fetch_macro_prices() -> List[Dict[str, Any]]:
    """
    Fetches live prices for macro indicators.
    """
    results = []
    # Batch fetch might be cleaner but loop is fine for < 10 items
    for name, ticker_sym in MACRO_TICKERS.items():
        try:
            ticker = yf.Ticker(ticker_sym)
            # fast_info is faster
            price = ticker.fast_info.last_price
            prev_close = ticker.fast_info.previous_close
            
            change = 0
            if prev_close:
                change = ((price - prev_close) / prev_close) * 100
                
            results.append({
                "name": name.replace("_", " ").title(),
                "symbol": ticker_sym,
                "price": round(price, 2),
                "changePercent": round(change, 2),
                "type": "bond" if "10y" in name else "commodity" if name in ["crude_oil", "gold", "silver"] else "currency"
            })
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            
    return results

def get_geo_data(commodity_type: str) -> List[Dict[str, Any]]:
    """
    Returns lat/lng data for the requested commodity.
    """
    return COMMODITY_LOCATIONS.get(commodity_type.lower(), [])
