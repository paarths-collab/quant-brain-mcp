import requests
import json

api_key = "6988cd035a3785.44084827"
url = "https://eodhd.com/api/screener"
params = {
    "api_token": api_key,
    "limit": 5,
    "fmt": "json",
    "filters": json.dumps([["exchange", "=", "NSE"]])
}

print(f"Testing EODHD API with key: {api_key}")
print(f"URL: {url}")
print(f"Params: {params}")

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"\nStatus code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nSuccess! Got {len(data) if isinstance(data, list) else 'unknown'} results")
        if isinstance(data, list) and len(data) > 0:
            print(f"First result: {data[0]}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Exception: {e}")
