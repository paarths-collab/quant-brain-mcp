
import requests
import json
import time

BASE_URL = "http://localhost:8001"

def print_res(name, res):
    print(f"\n--- {name} ---")
    if res.status_code == 200:
        print("SUCCESS")
        try:
            print(json.dumps(res.json(), indent=2)[:500] + "...")
        except:
            print(res.text[:500])
    else:
        print(f"FAILED ({res.status_code})")
        print(res.text)

def test_apis():
    # 1. Save Profile
    print("1. Testing Save Profile...")
    profile_payload = {
        "user_id": "test_user_1",
        "name": "Test Investor",
        "age": 35,
        "monthly_income": 10000,
        "monthly_savings": 2000,
        "risk_tolerance": "high",
        "horizon_years": 15,
        "primary_goal": "Retirement",
        "market": "US"
    }
    try:
        res = requests.post(f"{BASE_URL}/api/investor-profile/save", json=profile_payload)
        print_res("Save Profile", res)
    except Exception as e:
        print(f"Save Profile Failed: {e}")

    # 2. Load Profile
    print("\n2. Testing Load Profile...")
    try:
        res = requests.get(f"{BASE_URL}/api/investor-profile/load?user_id=test_user_1")
        print_res("Load Profile", res)
    except Exception as e:
        print(f"Load Profile Failed: {e}")

    # 3. Sector News
    print("\n3. Testing Sector News...")
    try:
        res = requests.get(f"{BASE_URL}/api/market-pulse/sector-news?limit=3")
        print_res("Sector News", res)
    except Exception as e:
        print(f"Sector News Failed: {e}")

    # 4. Sentiment (Mock)
    print("\n4. Testing Sentiment Pulse...")
    sentiment_payload = {
        "message": "I am worried about the market crashing",
        "tickers": ["SPY"],
        "market": "US"
    }
    try:
        # This might take a few seconds due to DDG/Tavily
        res = requests.post(f"{BASE_URL}/api/market-pulse/sentiment", json=sentiment_payload)
        print_res("Sentiment Pulse", res)
    except Exception as e:
        print(f"Sentiment Pulse Failed: {e}")

if __name__ == "__main__":
    test_apis()
