import sys
import os
# Add project root to path
sys.path.append(os.getcwd())

from backend.services.peer_comparison_service import fetch_peer_comparison

print("Starting debug...")
try:
    print("Testing AAPL...")
    res = fetch_peer_comparison("AAPL", limit=2)
    print("AAPL Success. Count:", res.get("count"))

    print("\nTesting RELIANCE.NS...")
    res = fetch_peer_comparison("RELIANCE.NS", limit=2)
    print("RELIANCE.NS Success. Count:", res.get("count"))
    if res.get("restricted"):
        print("Restricted:", res.get("message"))
    else:
        print("Rows:", len(res.get("rows", [])))
        for r in res.get("rows", []):
            print("-", r.get("symbol"))

except Exception as e:
    print("\nCRITICAL ERROR:", e)
    import traceback
    traceback.print_exc()
