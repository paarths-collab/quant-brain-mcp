from backend.services.sector_service import fetch_sector_performance
import json

def test_sectors():
    print("Testing sector performance fetch...")
    data = fetch_sector_performance()
    
    if data:
        print(f"Success! Got {len(data)} sectors.")
        print("Sample Sector:", data[0]['name'])
        print("Sample Stock:", data[0]['children'][0]['symbol'])
    else:
        print("Failed to fetch sector data.")

if __name__ == "__main__":
    test_sectors()
