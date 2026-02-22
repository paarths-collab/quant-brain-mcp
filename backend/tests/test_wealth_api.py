"""
Simple HTTP test for Wealth API endpoints
Tests that the routes are registered and accessible
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_health():
    """Test basic health endpoint"""
    print("\n" + "="*80)
    print("TEST 1: Health Check")
    print("="*80)
    try:
        response = requests.get(f"{API_BASE}/")
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_wealth_analyze():
    """Test wealth analysis endpoint"""
    print("\n" + "="*80)
    print("TEST 2: Wealth Analysis Endpoint")
    print("="*80)
    
    payload = {
        "user_input": "I'm 30 years old with $50,000 savings, moderate risk tolerance, want to invest for retirement",
        "market": "US"
    }
    
    print(f"\n📤 Request:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(
            f"{API_BASE}/api/wealth/analyze",
            json=payload,
            timeout=60
        )
        
        print(f"\n📥 Response:")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"Success: {data.get('success')}")
            print(f"Has Report: {'report' in data}")
            print(f"Has Stock: {'selected_stock' in data}")
            
            if data.get('selected_stock'):
                stock = data['selected_stock']
                print(f"\n📈 Recommended Stock:")
                print(f"  Ticker: {stock.get('Ticker')}")
                print(f"  Price: ${stock.get('Price', 0):.2f}")
            
            # Save full response
            with open('wealth_test_response.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Full response saved to: wealth_test_response.json")
            
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Is the backend server running?")
        print("   Start it with: python -m uvicorn backend.main:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

if __name__ == "__main__":
    print("\n🧪 AI Advisor API Test Suite")
    print("="*80)
    
    # Test 1: Health
    health_ok = test_health()
    
    if not health_ok:
        print("\n❌ Backend is not running. Please start it first:")
        print("   cd backend")
        print("   python -m uvicorn backend.main:app --reload --port 8000")
        exit(1)
    
    # Test 2: Wealth Analysis
    wealth_ok = test_wealth_analyze()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Wealth Analysis: {'✅ PASS' if wealth_ok else '❌ FAIL'}")
    
    if health_ok and wealth_ok:
        print("\n🎉 All tests passed! Backend is ready.")
    else:
        print("\n⚠️ Some tests failed. Check errors above.")
