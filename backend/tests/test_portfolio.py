import requests
import json
import time

BASE_URL = "http://localhost:8001/api/investor-profile"
MARKET_URL = "http://localhost:8001/api/market"

def print_res(name, res):
    print(f"\n--- {name} ---")
    if res.status_code == 200:
        print("SUCCESS")
        try:
            print(json.dumps(res.json(), indent=2))
        except:
            print(res.text)
    else:
        print(f"FAILED ({res.status_code})")
        print(res.text)

def run_tests():
    # 1. Reset/Create Profile
    print("1. Creating Profile...")
    requests.post(f"{BASE_URL}/save", json={
        "user_id": "test_trader",
        "name": "Trader Joe",
        "market": "US"
    })

    # 2. Get Initial Portfolio
    print("2. Get Initial Portfolio...")
    res = requests.get(f"{BASE_URL}/portfolio", params={"user_id": "test_trader"})
    print_res("Initial Portfolio", res)

    # 3. Buy AAPL
    print("3. Buy AAPL...")
    res = requests.post(f"{BASE_URL}/trade", json={
        "user_id": "test_trader",
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 10
    })
    print_res("Buy AAPL", res)

    # 4. Buy MSFT (using amount) - skipping amount logic for simplicity in test, using quantity
    print("4. Buy MSFT...")
    res = requests.post(f"{BASE_URL}/trade", json={
        "user_id": "test_trader",
        "symbol": "MSFT",
        "side": "buy",
        "quantity": 5
    })
    print_res("Buy MSFT", res)

    # 5. Get Portfolio (Should have AAPL and MSFT with values)
    print("5. Get Portfolio (Populated)...")
    res = requests.get(f"{BASE_URL}/portfolio", params={"user_id": "test_trader"})
    print_res("Portfolio with Holdings", res)

    # 6. Sell AAPL
    print("6. Sell 5 AAPL...")
    res = requests.post(f"{BASE_URL}/trade", json={
        "user_id": "test_trader",
        "symbol": "AAPL",
        "side": "sell",
        "quantity": 5
    })
    print_res("Sell AAPL", res)

    # 7. Final Portfolio
    print("7. Final Portfolio...")
    res = requests.get(f"{BASE_URL}/portfolio", params={"user_id": "test_trader"})
    print_res("Final Portfolio", res)

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"Test failed: {e}")
