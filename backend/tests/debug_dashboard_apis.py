
import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from backend.services.treemap_service import TreemapService
from backend.services.fred_service import FredService

async def debug_apis():
    print("--- Debugging Treemap API (Indices) ---")
    ts = TreemapService()
    # Test NIFTY 50
    try:
        nifty = await ts.get_stock_details('^NSEI', 'india')
        print(f"NIFTY 50 Raw Price Data: {nifty.get('price')}")
        print(f"NIFTY 50 Change %: {nifty.get('change_percent')}")
    except Exception as e:
        print(f"NIFTY Error: {e}")

    # Test Watchlist (Reliance)
    try:
        ril = await ts.get_stock_details('RELIANCE.NS', 'india')
        print(f"RELIANCE Raw Price Data: {ril.get('price')}")
    except Exception as e:
        print(f"RELIANCE Error: {e}")

    print("\n--- Debugging FRED API ---")
    fs = FredService()
    try:
        # Test getting a series
        series_id = 'SP500'
        data = await fs.get_latest_cached([series_id])
        print(f"FRED SP500 Data: {data}")
    except Exception as e:
        print(f"FRED Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_apis())
