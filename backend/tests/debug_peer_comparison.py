
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from backend.services.peer_comparison_service import fetch_peer_comparison
from backend.core.config import FMP_API_KEY, FINNHUB_API_KEY, PEERS_PREMIUM

def debug_peers():
    print("--- Debugging Peer Comparison ---")
    print(f"FMP_API_KEY Configured: {bool(FMP_API_KEY)}")
    print(f"FINNHUB_API_KEY Configured: {bool(FINNHUB_API_KEY)}")
    print(f"PEERS_PREMIUM: {PEERS_PREMIUM}")

    symbol = "AAPL"
    print(f"\nFetching peers for {symbol}...")
    try:
        result = fetch_peer_comparison(symbol, limit=5, debug=True)
        print(f"Count: {result.get('count')}")
        print(f"Rows: {len(result.get('rows', []))}")
        if result.get('debug'):
            print(f"Debug Info: {result['debug']}")
        
        if result.get('rows'):
            print(f"First Row: {result['rows'][0]}")
    except Exception as e:
        print(f"Error fetching peers: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_peers()
