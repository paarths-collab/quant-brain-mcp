import requests
import json

def test_chat():
    url = "http://localhost:8000/api/agent/chat"
    
    # Test 1: Codebase Introspection
    query_code = "How many classes are in backend/main.py?"
    print(f"\n--- Testing Query: {query_code} ---")
    try:
        response = requests.post(url, json={"query": query_code}, timeout=60)
        if response.status_code == 200:
            data = response.json()
            print("Status:", data.get("status"))
            print("Plan:", json.dumps(data.get("plan"), indent=2))
            print("Final Answer:", data.get("final_answer"))
        else:
            print("Error:", response.text)
    except Exception as e:
        print("Request failed:", e)

    # Test 2: Web Research + Finance (if keys available, otherwise might mock or fail gracefully)
    # query_web = "Find the best AI stocks and get the price of the top one."
    # print(f"\n--- Testing Query: {query_web} ---")
    # try:
    #     response = requests.post(url, json={"query": query_web}, timeout=60)
    #     if response.status_code == 200:
    #         data = response.json()
    #         print("Status:", data.get("status"))
    #         print("Final Answer:", data.get("final_answer"))
    #     else:
    #         print("Error:", response.text)
    # except Exception as e:
    #     print("Request failed:", e)

if __name__ == "__main__":
    test_chat()
