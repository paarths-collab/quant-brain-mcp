from backend.services.fundamentals_service import get_fundamentals_summary
from backend.core.config import FMP_API_KEY
import json

def test_fundamentals():
    print(f"API KEY Loaded: {FMP_API_KEY[:4]}***")
    symbol = "AAPL"
    print(f"Testing fundamentals for {symbol}...")
    data = get_fundamentals_summary(symbol)
    
    if data and data.get('name'):
        print(f"Success! Fetched data for {data['name']}")
        print("Market Cap:", data.get('marketCap'))
        print("Metrics:", json.dumps(data.get('metrics', {}), indent=2))
    else:
        print("Failed to fetch fundamentals.")

if __name__ == "__main__":
    test_fundamentals()
