import asyncio
import sys
import os

# Ensure backend can be imported
sys.path.append(os.getcwd())

from backend.services.eia_service import EIAService

async def test_eia():
    service = EIAService()
    print("Fetching Crude Oil Reserves...")
    try:
        reserves = service.get_crude_oil_reserves()
        if 'data' in reserves:
            print(f"Success: Got {len(reserves['data'])} records for reserves.")
            # Print first record to check structure
            if len(reserves['data']) > 0:
                print("Sample Data:", reserves['data'][0])
        else:
            print("Warning: No 'data' field in responses. Response keys:", reserves.keys())
            if 'error' in reserves:
                print("Error:", reserves['error'])
    except Exception as e:
        print(f"FAILED to fetch reserves: {e}")

    print("\nFetching Petroleum Summary...")
    try:
        summary = service.get_petroleum_summary()
        if 'data' in summary:
            print(f"Success: Got {len(summary['data'])} records for summary.")
        else:
            print("Warning: No 'data' field in responses. Response keys:", summary.keys())
    except Exception as e:
        print(f"FAILED to fetch summary: {e}")

if __name__ == "__main__":
    asyncio.run(test_eia())
